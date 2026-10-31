
import asyncio
import logging
from typing import Protocol

from app.events.engine import EventEngine
from app.events.processors.nft_processor import NFTEventProcessor
from app.events.schemas import BlockchainEvent, EventType
from app.schemas.blockchain_activity import EthereumContractLog


logger = logging.getLogger(__name__)


class ActivityLogProvider(Protocol):
    async def get_block_logs(
        self,
        block_number: int,
        contract_addresses: list[str] | None = None,
        topics: list | None = None,
    ) -> list[EthereumContractLog]:
        ...


class BlockEventPipeline:
    def __init__(
        self,
        activity_provider: ActivityLogProvider,
        nft_processor: NFTEventProcessor,
        event_engine: EventEngine,
        chain_id: int = 1,
    ) -> None:
        if chain_id <= 0:
            raise ValueError("chain_id must be positive.")

        self.activity_provider = activity_provider
        self.nft_processor = nft_processor
        self.event_engine = event_engine
        self.chain_id = chain_id

        self._inflight: dict[int, asyncio.Task[int]] = {}
        self._lock = asyncio.Lock()
        self._subscribed = False

    def start(self) -> None:
        if self._subscribed:
            return

        self.event_engine.subscribe(
            EventType.BLOCK_MINED,
            self.handle_block_event,
        )
        self._subscribed = True

    def stop(self) -> None:
        if not self._subscribed:
            return

        self.event_engine.unsubscribe(
            EventType.BLOCK_MINED,
            self.handle_block_event,
        )
        self._subscribed = False

    async def handle_block_event(
        self,
        event: BlockchainEvent,
    ) -> None:
        if event.event_type != EventType.BLOCK_MINED:
            return

        if event.chain_id != self.chain_id:
            return

        block_number = event.payload.get("block_number")

        if (
            not isinstance(block_number, int)
            or isinstance(block_number, bool)
            or block_number < 0
        ):
            logger.warning("Ignoring invalid block event payload.")
            return

        await self.process_block(block_number)

    async def process_block(self, block_number: int) -> int:
        if (
            not isinstance(block_number, int)
            or isinstance(block_number, bool)
            or block_number < 0
        ):
            raise ValueError("Invalid block number.")

        async with self._lock:
            task = self._inflight.get(block_number)

            if task is None:
                task = asyncio.create_task(
                    self._process_block(block_number)
                )
                self._inflight[block_number] = task

        try:
            return await asyncio.shield(task)
        finally:
            if task.done():
                async with self._lock:
                    if self._inflight.get(block_number) is task:
                        del self._inflight[block_number]

    async def _process_block(self, block_number: int) -> int:
        logger.info(
            "Processing Ethereum block %s",
            block_number,
        )

        logs = await self.activity_provider.get_block_logs(
            block_number=block_number,
        )

        count = await self.nft_processor.process_logs(logs)

        logger.info(
            "Processed block %s: %s NFT events dispatched",
            block_number,
            count,
        )

        return count
