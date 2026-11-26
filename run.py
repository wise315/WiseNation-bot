
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
from app.services.nft_blockchain_event_service import (
    NFTBlockchainEventService,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

ETHEREUM_CHAIN_ID = 1


async def supervise_runtime(
    polling_task: asyncio.Task,
    listener_task: asyncio.Task,
) -> None:
    """
    Monitor Telegram polling and Ethereum block listening.

    If either task exits, stop the other task.
    Propagate unexpected listener failures.
    """
    tasks = {polling_task, listener_task}

    try:
        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED,
        )

        if listener_task in done:
            # Propagate the listener's original exception.
            await listener_task

            raise RuntimeError(
                "Ethereum block listener stopped unexpectedly."
            )

        # Telegram polling completed first.
        await polling_task

    finally:
        for task in tasks:
            if not task.done():
                task.cancel()

        await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )




async def main() -> None:
    settings = get_settings()

    if not settings.telegram_bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not configured in the .env file."
        )

    bot = None
    blockchain = None

    listener_task = None
    polling_task = None

    block_listener = None
    block_pipeline = None

    try:
        # Protect resource acquisition from partial startup failures.
        bot = create_bot(settings.telegram_bot_token)

        dispatcher = create_dispatcher()

        blockchain = BlockchainService()

        async with AsyncSessionLocal() as db_session:
            try:
                # Initialize persistence services.
                checkpoint_service = BlockCheckpointService(
                    db_session
                )

                canonical_block_service = CanonicalBlockService(
                    session=checkpoint_service.session,
                )

                nft_event_service = NFTBlockchainEventService(
                    session=db_session,
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

                # Preserve RPC retry and failover functionality.
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
                    nft_event_service=nft_event_service,
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

                polling_task = asyncio.create_task(
                    dispatcher.start_polling(bot),
                    name="telegram-polling",
                )

                await supervise_runtime(
                    polling_task,
                    listener_task,
                )

            finally:
                logger.info(
                    "Shutting down blockchain monitoring..."
                )

                try:
                    if block_listener is not None:
                        block_listener.stop()

                finally:
                    try:
                        # Include partially initialized runtime tasks.
                        runtime_tasks = [
                            task
                            for task in (
                                polling_task,
                                listener_task,
                            )
                            if task is not None
                        ]

                        for task in runtime_tasks:
                            if not task.done():
                                task.cancel()

                        if runtime_tasks:
                            await asyncio.gather(
                                *runtime_tasks,
                                return_exceptions=True,
                            )

                    finally:
                        # Drain processing before the database
                        # session exits.
                        if block_pipeline is not None:
                            await block_pipeline.shutdown()

    finally:
        try:
            if blockchain is not None:
                await blockchain.ethereum.close()

        finally:
            if bot is not None:
                await bot.session.close()

    logger.info("WiseNation Bot stopped.")



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user.")
