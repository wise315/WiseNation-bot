
import asyncio
import logging

from app.bot.bot import create_bot, create_dispatcher
from app.blockchain.providers.ethereum_activity import (
    EthereumActivityProvider,
)
from app.blockchain.service import BlockchainService
from app.core.config import get_settings
from app.database.session import AsyncSessionLocal
from app.events.engine import EventEngine
from app.events.processors.block_pipeline import BlockEventPipeline
from app.events.processors.nft_decoder import NFTEventDecoder
from app.events.processors.nft_processor import NFTEventProcessor
from app.events.subscribers.ethereum_blocks import EthereumBlockListener
from app.services.block_checkpoint_service import BlockCheckpointService
from app.services.canonical_block_service import CanonicalBlockService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

ETHEREUM_CHAIN_ID = 1


async def main() -> None:
    settings = get_settings()

    if not settings.telegram_bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not configured in the .env file."
        )

    bot = create_bot(settings.telegram_bot_token)
    dispatcher = create_dispatcher()
    blockchain = BlockchainService()

    listener_task = None
    block_listener = None
    block_pipeline = None

    try:
        async with AsyncSessionLocal() as db_session:
            checkpoint_service = BlockCheckpointService(
                db_session
            )

            # Canonical block tracking uses the same DB session
            # as checkpoint persistence.
            canonical_block_service = CanonicalBlockService(
                session=checkpoint_service.session,
            )

            # Recover the last successfully processed block.
            checkpoint = await checkpoint_service.get_checkpoint(
                chain_id=ETHEREUM_CHAIN_ID,
            )

            start_from_block = (
                checkpoint.last_processed_block
                if checkpoint is not None
                else None
            )

            if start_from_block is None:
                logger.info(
                    "No Ethereum checkpoint found. "
                    "Listener will initialize at the latest block."
                )
            else:
                logger.info(
                    "Recovered Ethereum checkpoint: block %s",
                    start_from_block,
                )

            # Initialize event engine.
            event_engine = EventEngine()

            # Pass the EthereumProvider wrapper to preserve
            # RPC retry and failover functionality.
            activity_provider = EthereumActivityProvider(
                blockchain.ethereum,
            )

            nft_decoder = NFTEventDecoder(
                chain_id=ETHEREUM_CHAIN_ID,
            )

            nft_processor = NFTEventProcessor(
                decoder=nft_decoder,
                event_engine=event_engine,
            )

            # Initialize canonical-aware block pipeline.
            block_pipeline = BlockEventPipeline(
                activity_provider=activity_provider,
                nft_processor=nft_processor,
                event_engine=event_engine,
                chain_id=ETHEREUM_CHAIN_ID,
                checkpoint_service=checkpoint_service,
                canonical_block_service=canonical_block_service,
            )

            # Register the pipeline before starting the listener.
            block_pipeline.start()

            block_listener = EthereumBlockListener(
                provider=blockchain.ethereum,
                event_engine=event_engine,
                chain_id=ETHEREUM_CHAIN_ID,
                start_from_block=start_from_block,
            )

            print("=" * 50)
            print("WiseNation Bot")
            print("=" * 50)
            print(f"Environment: {settings.app_env}")
            print(f"Ethereum checkpoint: {start_from_block}")
            print("Telegram bot starting...")
            print("Ethereum block monitoring starting...")

            listener_task = asyncio.create_task(
                block_listener.run(),
                name="ethereum-block-listener",
            )

            try:
                await dispatcher.start_polling(bot)

            finally:
                logger.info(
                    "Shutting down blockchain monitoring..."
                )

                if block_listener is not None:
                    block_listener.stop()

                if listener_task is not None:
                    try:
                        await listener_task
                    except asyncio.CancelledError:
                        pass
                    except Exception:
                        logger.exception(
                            "Ethereum block listener stopped "
                            "with an error."
                        )

                if block_pipeline is not None:
                    block_pipeline.stop()

    finally:
        try:
            await blockchain.ethereum.close()
        finally:
            await bot.session.close()

    logger.info("WiseNation Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user.")
