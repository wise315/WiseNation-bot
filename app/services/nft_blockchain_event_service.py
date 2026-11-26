
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.nft_blockchain_event import (
    NFTBlockchainEvent,
)
from app.events.schemas import BlockchainEvent, EventType


class NFTBlockchainEventService:
    SUPPORTED_TYPES = frozenset({
        EventType.NFT_MINT,
        EventType.NFT_TRANSFER,
    })

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _validate_chain_id(chain_id: int) -> None:
        if (
            isinstance(chain_id, bool)
            or not isinstance(chain_id, int)
            or chain_id <= 0
        ):
            raise ValueError(
                "chain_id must be a positive integer."
            )

    @staticmethod
    def _validate_block_number(block_number: int) -> None:
        if (
            isinstance(block_number, bool)
            or not isinstance(block_number, int)
            or block_number < 0
        ):
            raise ValueError(
                "block_number must be non-negative."
            )

    @staticmethod
    def _normalize_hash(value: str, name: str) -> str:
        if (
            not isinstance(value, str)
            or len(value) != 66
            or not value.startswith("0x")
        ):
            raise ValueError(
                f"{name} must be a 0x-prefixed 32-byte hash."
            )

        try:
            bytes.fromhex(value[2:])
        except ValueError as exc:
            raise ValueError(
                f"{name} contains invalid hexadecimal."
            ) from exc

        return value.lower()

    @staticmethod
    def _validate_index(value: int, name: str) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise ValueError(
                f"{name} must be a non-negative integer."
            )

    async def save_event(
        self,
        event: BlockchainEvent,
        block_hash: str,
    ) -> bool:
        """
        Persist one decoded NFT event.

        Returns True if inserted, False if already present.

        Does not commit the database transaction.
        """
        if event.event_type not in self.SUPPORTED_TYPES:
            raise ValueError(
                f"Unsupported NFT event type: {event.event_type}"
            )

        self._validate_chain_id(event.chain_id)

        payload = event.payload

        required_fields = (
            "block_number",
            "transaction_hash",
            "log_index",
        )

        for field in required_fields:
            if field not in payload:
                raise ValueError(
                    f"NFT event payload missing: {field}"
                )

        block_number = payload["block_number"]
        transaction_hash = self._normalize_hash(
            payload["transaction_hash"],
            "transaction_hash",
        )
        block_hash = self._normalize_hash(
            block_hash,
            "block_hash",
        )

        log_index = payload["log_index"]
        batch_index = payload.get("batch_index", 0)

        self._validate_block_number(block_number)
        self._validate_index(log_index, "log_index")
        self._validate_index(batch_index, "batch_index")

        # Normalize the persisted JSON representation.
        # Do not modify the original BlockchainEvent.
        stored_payload = dict(payload)
        stored_payload["transaction_hash"] = transaction_hash

        statement = (
            insert(NFTBlockchainEvent)
            .values(
                chain_id=event.chain_id,
                block_number=block_number,
                block_hash=block_hash,
                transaction_hash=transaction_hash,
                log_index=log_index,
                batch_index=batch_index,
                event_type=event.event_type.value,
                payload=stored_payload,
                is_canonical=True,
            )
            .on_conflict_do_nothing(
                constraint="uq_nft_blockchain_event_identity"
            )
            .returning(NFTBlockchainEvent.id)
        )

        result = await self.session.execute(statement)

        inserted_id = result.scalar_one_or_none()

        return inserted_id is not None

    async def save_events(
        self,
        events: Sequence[BlockchainEvent],
        block_hash: str,
    ) -> int:
        """
        Save multiple decoded events.

        Returns the number of newly inserted records.
        Does not commit.
        """
        inserted = 0

        for event in events:
            if await self.save_event(event, block_hash):
                inserted += 1

        return inserted
    
    async def save_new_events(
        self,
        events: Sequence[BlockchainEvent],
        block_hash: str,
    ) -> list[BlockchainEvent]:
        newly_inserted = []
        
        
        for event in events:
            inserted = await self.save_event(
                event,
                block_hash,
            )

            if inserted:
                newly_inserted.append(event)

        return newly_inserted

    async def get_block_events(
        self,
        chain_id: int,
        block_number: int,
        canonical_only: bool = True,
    ) -> list[NFTBlockchainEvent]:
        self._validate_chain_id(chain_id)
        self._validate_block_number(block_number)

        statement = select(NFTBlockchainEvent).where(
            NFTBlockchainEvent.chain_id == chain_id,
            NFTBlockchainEvent.block_number == block_number,
        )

        if canonical_only:
            statement = statement.where(
                NFTBlockchainEvent.is_canonical.is_(True)
            )

        statement = statement.order_by(
            NFTBlockchainEvent.log_index,
            NFTBlockchainEvent.batch_index,
            NFTBlockchainEvent.id,
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def get_transaction_events(
        self,
        chain_id: int,
        transaction_hash: str,
        canonical_only: bool = True,
    ) -> list[NFTBlockchainEvent]:
        self._validate_chain_id(chain_id)

        transaction_hash = self._normalize_hash(
            transaction_hash,
            "transaction_hash",
        )

        statement = select(NFTBlockchainEvent).where(
            NFTBlockchainEvent.chain_id == chain_id,
            NFTBlockchainEvent.transaction_hash == transaction_hash,
        )

        if canonical_only:
            statement = statement.where(
                NFTBlockchainEvent.is_canonical.is_(True)
            )

        statement = statement.order_by(
            NFTBlockchainEvent.block_number,
            NFTBlockchainEvent.log_index,
            NFTBlockchainEvent.batch_index,
            NFTBlockchainEvent.id,
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def mark_blocks_orphaned(
        self,
        chain_id: int,
        ancestor_block: int,
    ) -> int:
        """
        Mark events above the ancestor as non-canonical.

        Returns the number of updated rows.
        Does not commit.
        """
        self._validate_chain_id(chain_id)
        self._validate_block_number(ancestor_block)

        statement = (
            update(NFTBlockchainEvent)
            .where(
                NFTBlockchainEvent.chain_id == chain_id,
                NFTBlockchainEvent.block_number > ancestor_block,
                NFTBlockchainEvent.is_canonical.is_(True),
            )
            .values(is_canonical=False)
        )

        result = await self.session.execute(statement)

        return result.rowcount
