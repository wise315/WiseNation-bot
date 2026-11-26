
import asyncio
import logging
from typing import Protocol

from app.events.engine import EventEngine
from app.events.processors.nft_processor import NFTEventProcessor
from app.events.schemas import BlockchainEvent, EventType
from app.schemas.blockchain_activity import EthereumContractLog
from app.services.block_checkpoint_service import BlockCheckpointService
from app.services.canonical_block_service import (
    CanonicalBlockConflictError,
    CanonicalBlockService,
)
from app.services.nft_blockchain_event_service import (
    NFTBlockchainEventService,
)


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
        checkpoint_service: BlockCheckpointService | None = None,
        canonical_block_service: CanonicalBlockService | None = None,
        nft_event_service: NFTBlockchainEventService | None = None,
    ) -> None:
        if (
            isinstance(chain_id, bool)
            or not isinstance(chain_id, int)
            or chain_id <= 0
        ):
            raise ValueError("chain_id must be positive.")

        if (
            canonical_block_service is not None
            and checkpoint_service is None
        ):
            raise ValueError(
                "Canonical tracking requires a checkpoint service."
            )

        if (
            canonical_block_service is not None
            and canonical_block_service.session
            is not checkpoint_service.session
        ):
            raise ValueError(
                "Canonical and checkpoint services must share "
                "the same database session."
            )

        if nft_event_service is not None:
            if checkpoint_service is None:
                raise ValueError(
                    "NFT event persistence requires a checkpoint service."
                )

            if canonical_block_service is None:
                raise ValueError(
                    "NFT event persistence requires canonical block tracking."
                )

            if nft_event_service.session is not checkpoint_service.session:
                raise ValueError(
                    "NFT persistence and checkpoint services must share "
                    "the same database session."
                )

        self.activity_provider = activity_provider
        self.nft_processor = nft_processor
        self.event_engine = event_engine
        self.chain_id = chain_id
        self.checkpoint_service = checkpoint_service
        self.canonical_block_service = canonical_block_service
        self.nft_event_service = nft_event_service

        self._inflight: dict[int, asyncio.Task[int]] = {}
        self._lock = asyncio.Lock()

        # Serialize block processing and database transactions.
        self._processing_lock = asyncio.Lock()

        self._subscribed = False
        
        # Prevent new processing requests during shutdown.
        self._shutting_down = False

    def start(self) -> None:
        
        if self._shutting_down:
            raise RuntimeError(
                "Block pipeline is shutting down."
            )
        
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
        
    async def shutdown(self) -> None:
        """ Stop accepting new blocks and drain existing tasks.

    Existing block-processing tasks are allowed to finish
    before the shared database session is closed."""
    
        async with self._lock:
            self._shutting_down = True
            
            self.stop()

            tasks = list(self._inflight.values())
            
        logger.info(
            "Shutting down block pipeline: waiting for %s inflight tasks...",
            len(tasks),
        )
        
        if tasks:
            drain = asyncio.gather(
                *tasks,
                return_exceptions=True,
            )
            
            try:
                results =  await asyncio.shield(drain)
                
            except asyncio.CancelledError:
                # Do not abandon active database operations
            # on the first shutdown cancellation.
                await asyncio.shield(drain)
                raise
            
            for result in results:
                if isinstance(result, BaseException):
                    logger.error(
                        "Block processing task failed during shutdown: %s",
                        result,
                    )
        
        async with self._lock:
            completed_blocks = [
                block_number
                for block_number, task in self._inflight.items()
                if task.done()
            ]
            
            for block_number in completed_blocks:
                del self._inflight[block_number]
                
        logger.info("Block pipeline shutdown completed.")
        

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
            
            if self._shutting_down:
                raise RuntimeError(
                    "Block pipeline is shutting down."
                )
            
            task = self._inflight.get(block_number)

            if task is None:
                task = asyncio.create_task(
                    self._process_block_sequentially(block_number)
                )
                self._inflight[block_number] = task

                task.add_done_callback(
                    lambda completed, height=block_number:
                    asyncio.create_task(
                        self._cleanup_task(height, completed)
                    )
                )

        return await asyncio.shield(task)

    async def _process_block_sequentially(
        self,
        block_number: int,
    ) -> int:
        async with self._processing_lock:
            return await self._process_block(block_number)

    async def _cleanup_task(
        self,
        block_number: int,
        task: asyncio.Task[int],
    ) -> None:
        # Retrieve exceptions even when the original caller
        # was cancelled while awaiting a shielded task.
        if task.done() and not task.cancelled():
            task.exception()
            
        async with self._lock:
            if self._inflight.get(block_number) is task:
                del self._inflight[block_number]

    async def _get_block_metadata(
        self,
        block_number: int,
    ) -> tuple[str, str]:
        getter = getattr(
            self.activity_provider,
            "get_block_metadata",
            None,
        )

        if getter is None:
            raise RuntimeError(
                "Activity provider does not support "
                "get_block_metadata()."
            )

        metadata = await getter(block_number)

        if isinstance(metadata, tuple):
            if len(metadata) != 2:
                raise ValueError(
                    "Block metadata must contain exactly two hashes."
                )

            block_hash, parent_hash = metadata

        elif isinstance(metadata, dict):
            block_hash = metadata["block_hash"]
            parent_hash = metadata["parent_hash"]

        else:
            block_hash = metadata.block_hash
            parent_hash = metadata.parent_hash

        return block_hash, parent_hash

    async def _check_canonical_history(
        self,
        block_number: int,
        block_hash: str,
        parent_hash: str,
    ) -> None:
        service = self.canonical_block_service

        existing = await service.get_block(
            self.chain_id,
            block_number,
        )

        if existing is not None:
            if (
                existing.block_hash.lower() != block_hash.lower()
                or existing.parent_hash.lower() != parent_hash.lower()
            ):
                raise CanonicalBlockConflictError(
                    f"Reorganization detected at block {block_number}."
                )

        if block_number == 0:
            return

        previous = await service.get_block(
            self.chain_id,
            block_number - 1,
        )

        if (
            previous is not None
            and previous.block_hash.lower() != parent_hash.lower()
        ):
            raise CanonicalBlockConflictError(
                f"Parent hash mismatch at block {block_number}."
            )

    async def _process_block(self, block_number: int) -> int:
        logger.info(
            "Processing Ethereum block %s",
            block_number,
        )

        session = (
            self.checkpoint_service.session
            if self.checkpoint_service is not None
            else None
        )

        events = None

        # Database operations and commit.
        try:
            block_hash = None
            parent_hash = None

            if self.canonical_block_service is not None:
                block_hash, parent_hash = (
                    await self._get_block_metadata(block_number)
                )

                await self._check_canonical_history(
                    block_number,
                    block_hash,
                    parent_hash,
                )

            logs = await self.activity_provider.get_block_logs(
                block_number=block_number,
            )

            if self.nft_event_service is not None:
                # Decode without publishing.
                decoded_events = self.nft_processor.decode_logs(logs)

                # Persist using the shared database session.
                events = await self.nft_event_service.save_new_events(
                    decoded_events,
                    block_hash,
                )

                count = len(events)

            else:
                # Preserve legacy behavior.
                count = await self.nft_processor.process_logs(logs)

            if self.canonical_block_service is not None:
                await self.canonical_block_service.save_block(
                    chain_id=self.chain_id,
                    block_number=block_number,
                    block_hash=block_hash,
                    parent_hash=parent_hash,
                )

            if self.checkpoint_service is not None:
                await self.checkpoint_service.save_checkpoint(
                    chain_id=self.chain_id,
                    block_number=block_number,
                    block_hash=block_hash,
                )

            if session is not None:
                await session.commit()

        except BaseException:
            if session is not None:
                await session.rollback()
            raise

        # Outside the transaction rollback handler.
        # A subscriber failure cannot undo committed database changes.
        if events:
            await self.nft_processor.publish_events(events)

        logger.info(
            "Processed block %s: %s NFT events dispatched",
            block_number,
            count,
        )

        return count
