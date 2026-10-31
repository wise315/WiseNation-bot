
import asyncio
import logging
from typing import Protocol

from app.events.engine import EventEngine
from app.events.schemas import BlockchainEvent, EventType


logger = logging.getLogger(__name__)


class BlockNumberProvider(Protocol):
    async def get_block_number(self) -> int:
        ...


class EthereumBlockListener:
    def __init__(
        self,
        provider: BlockNumberProvider,
        event_engine: EventEngine,
        chain_id: int = 1,
        poll_interval: float = 5.0,
        start_from_block: int | None = None,
    ) -> None:
        if chain_id <= 0:
            raise ValueError("chain_id must be positive.")

        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive.")

        if start_from_block is not None and start_from_block < 0:
            raise ValueError("start_from_block cannot be negative.")

        self.provider = provider
        self.event_engine = event_engine
        self.chain_id = chain_id
        self.poll_interval = poll_interval

        self.last_processed_block = start_from_block
        self._stop_event = asyncio.Event()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    async def poll_once(self) -> int:
        latest_block = await self.provider.get_block_number()

        if not isinstance(latest_block, int) or isinstance(
            latest_block, bool
        ):
            raise TypeError(
                "Ethereum provider returned an invalid block number."
            )

        if latest_block < 0:
            raise ValueError("Block number cannot be negative.")

        if self.last_processed_block is None:
            self.last_processed_block = latest_block
            logger.info(
                "Ethereum block listener initialized at block %s",
                latest_block,
            )
            return 0

        if latest_block <= self.last_processed_block:
            return 0

        published = 0

        for block_number in range(
            self.last_processed_block + 1,
            latest_block + 1,
        ):
            if self._stop_event.is_set():
                break

            event = BlockchainEvent(
                event_type=EventType.BLOCK_MINED,
                source="ethereum_rpc",
                chain_id=self.chain_id,
                payload={
                    "block_number": block_number,
                },
            )

            await self.event_engine.publish(event)

            self.last_processed_block = block_number
            published += 1

        return published

    async def run(self) -> None:
        if self._running:
            raise RuntimeError(
                "Ethereum block listener is already running."
            )

        self._running = True
        self._stop_event.clear()

        logger.info(
            "Starting Ethereum block listener for chain %s",
            self.chain_id,
        )

        try:
            while not self._stop_event.is_set():
                try:
                    await self.poll_once()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception(
                        "Ethereum block listener polling failed."
                    )

                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.poll_interval,
                    )
                except asyncio.TimeoutError:
                    pass
        finally:
            self._running = False
            logger.info("Ethereum block listener stopped.")

    def stop(self) -> None:
        self._stop_event.set()
