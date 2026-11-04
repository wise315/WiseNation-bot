
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

    async with AsyncSessionLocal() as db_session:
        checkpoint_service = BlockCheckpointService(db_session)

        # Recover the last successfully processed Ethereum block.
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

        # Create the event processing components.
        event_engine = EventEngine()

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

        block_pipeline = BlockEventPipeline(
            activity_provider=activity_provider,
            nft_processor=nft_processor,
            event_engine=event_engine,
            chain_id=ETHEREUM_CHAIN_ID,
            checkpoint_service=checkpoint_service,
        )

        # Register the block pipeline before starting the listener.
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
            logger.info("Shutting down blockchain monitoring...")

    block_listener.stop()

    try:
        await listener_task
    finally:
        block_pipeline.stop()

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
