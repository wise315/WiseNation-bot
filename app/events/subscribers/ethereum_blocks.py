import asyncio
import logging
import math
from typing import Protocol

from app.events.engine import EventEngine
from app.events.schemas import BlockchainEvent, EventType

logger = logging.getLogger(__name__)


class EthereumListenerFatalError(RuntimeError):
    """Raised when Ethereum polling exhausts its retry budget."""


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
        max_consecutive_failures: int = 5,
        initial_retry_delay: float = 2.0,
        max_retry_delay: float = 30.0,
    ) -> None:
        if chain_id <= 0:
            raise ValueError("chain_id must be positive.")

        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive.")

        if start_from_block is not None and start_from_block < 0:
            raise ValueError("start_from_block cannot be negative.")

        if (
            isinstance(max_consecutive_failures, bool)
            or not isinstance(max_consecutive_failures, int)
            or max_consecutive_failures < 1
        ):
            raise ValueError(
                "max_consecutive_failures must be a positive integer."
            )

        if (
            isinstance(initial_retry_delay, bool)
            or not isinstance(initial_retry_delay, (int, float))
            or not math.isfinite(initial_retry_delay)
            or initial_retry_delay <= 0
        ):
            raise ValueError(
                "initial_retry_delay must be a positive finite number."
            )

        if (
            isinstance(max_retry_delay, bool)
            or not isinstance(max_retry_delay, (int, float))
            or not math.isfinite(max_retry_delay)
            or max_retry_delay < initial_retry_delay
        ):
            raise ValueError(
                "max_retry_delay must be finite and greater than "
                "or equal to initial_retry_delay."
            )

        self.provider = provider
        self.event_engine = event_engine
        self.chain_id = chain_id
        self.poll_interval = poll_interval
        self.max_consecutive_failures = max_consecutive_failures
        self.initial_retry_delay = initial_retry_delay
        self.max_retry_delay = max_retry_delay
        self.last_processed_block = start_from_block

        self._stop_event = asyncio.Event()
        self._running = False
        self._consecutive_failures = 0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    async def poll_once(self) -> int:
        latest_block = await self.provider.get_block_number()

        if not isinstance(latest_block, int) or isinstance(latest_block, bool):
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
                payload={"block_number": block_number},
            )

            await self.event_engine.publish(event, raise_on_error=True)

            self.last_processed_block = block_number
            published += 1

        return published

    async def _wait_or_stop(self, delay: float) -> None:
        """Wait for the specified delay or an immediate stop request."""
        try:
            await asyncio.wait_for(
                self._stop_event.wait(),
                timeout=delay,
            )
        except asyncio.TimeoutError:
            pass

    async def run(self) -> None:
        if self._running:
            raise RuntimeError("Ethereum block listener is already running.")

        self._running = True
        self._stop_event.clear()
        self._consecutive_failures = 0
        retry_delay = self.initial_retry_delay

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
                except Exception as exc:
                    self._consecutive_failures += 1

                    logger.exception(
                        "Ethereum block listener polling failed (%s/%s).",
                        self._consecutive_failures,
                        self.max_consecutive_failures,
                    )

                    if self._stop_event.is_set():
                        break

                    if (
                        self._consecutive_failures
                        >= self.max_consecutive_failures
                    ):
                        raise EthereumListenerFatalError(
                            "Ethereum block listener exceeded "
                            f"{self._consecutive_failures} consecutive "
                            "polling failures."
                        ) from exc

                    logger.warning(
                        "Retrying Ethereum block listener in %.2f seconds...",
                        retry_delay,
                    )

                    await self._wait_or_stop(retry_delay)
                    retry_delay = min(retry_delay * 2, self.max_retry_delay)
                else:
                    if self._consecutive_failures > 0:
                        logger.info(
                            "Ethereum block listener recovered after "
                            "%s consecutive failures.",
                            self._consecutive_failures,
                        )

                    self._consecutive_failures = 0
                    retry_delay = self.initial_retry_delay

                    if self._stop_event.is_set():
                        break

                    await self._wait_or_stop(self.poll_interval)
        finally:
            self._running = False
            logger.info("Ethereum block listener stopped.")

    def stop(self) -> None:
        self._stop_event.set()