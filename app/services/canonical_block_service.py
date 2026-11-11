
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.canonical_block import CanonicalBlock


class CanonicalBlockConflictError(Exception):
    """A different block already exists at the same height."""


class CanonicalBlockService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _validate_chain_and_block(
        chain_id: int,
        block_number: int,
    ) -> None:
        if (
            isinstance(chain_id, bool)
            or not isinstance(chain_id, int)
            or chain_id <= 0
        ):
            raise ValueError("chain_id must be a positive integer.")

        if (
            isinstance(block_number, bool)
            or not isinstance(block_number, int)
            or block_number < 0
        ):
            raise ValueError(
                "block_number must be a non-negative integer."
            )

    @staticmethod
    def _validate_hash(value: str, name: str) -> None:
        if (
            not isinstance(value, str)
            or len(value) != 66
            or not value.startswith("0x")
        ):
            raise ValueError(
                f"{name} must be a 0x-prefixed 32-byte hex string."
            )

        try:
            bytes.fromhex(value[2:])
        except ValueError as exc:
            raise ValueError(
                f"{name} contains invalid hexadecimal characters."
            ) from exc

    async def get_block(
        self,
        chain_id: int,
        block_number: int,
    ) -> CanonicalBlock | None:
        self._validate_chain_and_block(chain_id, block_number)

        statement = select(CanonicalBlock).where(
            CanonicalBlock.chain_id == chain_id,
            CanonicalBlock.block_number == block_number,
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def save_block(
        self,
        chain_id: int,
        block_number: int,
        block_hash: str,
        parent_hash: str,
    ) -> CanonicalBlock:
        self._validate_chain_and_block(chain_id, block_number)
        self._validate_hash(block_hash, "block_hash")
        self._validate_hash(parent_hash, "parent_hash")

        block_hash = block_hash.lower()
        parent_hash = parent_hash.lower()

        existing = await self.get_block(chain_id, block_number)

        if existing is not None:
            if (
                existing.block_hash.lower() != block_hash
                or existing.parent_hash.lower() != parent_hash
            ):
                raise CanonicalBlockConflictError(
                    f"Conflicting canonical block at "
                    f"chain={chain_id}, height={block_number}."
                )

            return existing

        block = CanonicalBlock(
            chain_id=chain_id,
            block_number=block_number,
            block_hash=block_hash,
            parent_hash=parent_hash,
        )

        self.session.add(block)
        await self.session.flush()

        return block

    async def delete_blocks_after(
        self,
        chain_id: int,
        block_number: int,
    ) -> int:
        """
        Delete canonical block records above a given height.

        The caller must handle checkpoint rollback and commit
        the transaction. This method does not commit.
        """
        self._validate_chain_and_block(chain_id, block_number)

        statement = delete(CanonicalBlock).where(
            CanonicalBlock.chain_id == chain_id,
            CanonicalBlock.block_number > block_number,
        )

        result = await self.session.execute(statement)
        await self.session.flush()

        return result.rowcount

    async def get_latest_block(
        self,
        chain_id: int,
    ) -> CanonicalBlock | None:
        if (
            isinstance(chain_id, bool)
            or not isinstance(chain_id, int)
            or chain_id <= 0
        ):
            raise ValueError("chain_id must be a positive integer.")

        statement = (
            select(CanonicalBlock)
            .where(CanonicalBlock.chain_id == chain_id)
            .order_by(CanonicalBlock.block_number.desc())
            .limit(1)
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
