
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.block_checkpoint import BlockCheckpoint


class BlockCheckpointService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_checkpoint(
        self,
        chain_id: int,
    ) -> BlockCheckpoint | None:
        if isinstance(chain_id, bool) or chain_id <= 0:
            raise ValueError("chain_id must be positive.")

        result = await self.session.execute(
            select(BlockCheckpoint).where(
                BlockCheckpoint.chain_id == chain_id
            )
        )

        return result.scalar_one_or_none()

    async def save_checkpoint(
        self,
        chain_id: int,
        block_number: int,
        block_hash: str | None = None,
    ) -> BlockCheckpoint:
        if isinstance(chain_id, bool) or chain_id <= 0:
            raise ValueError("chain_id must be positive.")

        if (
            isinstance(block_number, bool)
            or not isinstance(block_number, int)
            or block_number < 0
        ):
            raise ValueError(
                "block_number must be a non-negative integer."
            )

        if block_hash is not None:
            if (
                not isinstance(block_hash, str)
                or len(block_hash) != 66
                or not block_hash.startswith("0x")
            ):
                raise ValueError(
                    "block_hash must be a 66-character hex string."
                )

            try:
                bytes.fromhex(block_hash[2:])
            except ValueError as exc:
                raise ValueError(
                    "block_hash must contain valid hexadecimal characters."
                ) from exc

        table = BlockCheckpoint.__table__

        statement = insert(table).values(
            chain_id=chain_id,
            last_processed_block=block_number,
            block_hash=block_hash,
            updated_at=datetime.now(timezone.utc),
        )

        statement = statement.on_conflict_do_update(
            constraint="uq_block_checkpoints_chain_id",
            set_={
                "last_processed_block": statement.excluded.last_processed_block,
                "block_hash": statement.excluded.block_hash,
                "updated_at": statement.excluded.updated_at,
            },
            where=(
                table.c.last_processed_block
                < statement.excluded.last_processed_block
            ),
        )

        await self.session.execute(statement)
        await self.session.flush()

        result = await self.session.execute(
            select(BlockCheckpoint)
            .where(BlockCheckpoint.chain_id == chain_id)
            .execution_options(populate_existing=True)
        )

        checkpoint = result.scalar_one()

        return checkpoint
