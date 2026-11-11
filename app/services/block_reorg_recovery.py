
import logging
from dataclasses import dataclass

from app.services.block_checkpoint_service import (
    BlockCheckpointService,
)
from app.services.canonical_block_service import (
    CanonicalBlockService,
)


logger = logging.getLogger(__name__)


class ReorgRecoveryError(Exception):
    """The requested rollback cannot be performed safely."""


@dataclass(frozen=True)
class ReorgRollbackResult:
    chain_id: int
    previous_checkpoint: int
    restored_checkpoint: int
    deleted_blocks: int


class BlockReorgRecoveryService:
    def __init__(
        self,
        canonical_service: CanonicalBlockService,
        checkpoint_service: BlockCheckpointService,
    ) -> None:
        if (
            canonical_service.session
            is not checkpoint_service.session
        ):
            raise ValueError(
                "Canonical and checkpoint services must "
                "share the same database session."
            )

        self.canonical_service = canonical_service
        self.checkpoint_service = checkpoint_service
        self.session = checkpoint_service.session

    async def rollback_to_ancestor(
        self,
        chain_id: int,
        ancestor_block: int,
        expected_checkpoint: int | None = None,
        expected_ancestor_hash: str | None = None,
    ) -> ReorgRollbackResult:
        if (
            isinstance(chain_id, bool)
            or not isinstance(chain_id, int)
            or chain_id <= 0
        ):
            raise ValueError(
                "chain_id must be a positive integer."
            )

        if (
            isinstance(ancestor_block, bool)
            or not isinstance(ancestor_block, int)
            or ancestor_block < 0
        ):
            raise ValueError(
                "ancestor_block must be non-negative."
            )

        if expected_checkpoint is not None and (
            isinstance(expected_checkpoint, bool)
            or not isinstance(expected_checkpoint, int)
            or expected_checkpoint < 0
        ):
            raise ValueError(
                "expected_checkpoint must be non-negative."
            )

        if expected_ancestor_hash is not None:
            if (
                not isinstance(expected_ancestor_hash, str)
                or len(expected_ancestor_hash) != 66
                or not expected_ancestor_hash.startswith("0x")
            ):
                raise ValueError(
                    "expected_ancestor_hash must be a "
                    "0x-prefixed 32-byte hex string."
                )

            try:
                bytes.fromhex(expected_ancestor_hash[2:])
            except ValueError as exc:
                raise ValueError(
                    "expected_ancestor_hash is not valid hex."
                ) from exc

        try:
            checkpoint = (
                await self.checkpoint_service.get_checkpoint(
                    chain_id
                )
            )

            if checkpoint is None:
                raise ReorgRecoveryError(
                    "No checkpoint exists for this chain."
                )

            current_height = checkpoint.last_processed_block

            if (
                expected_checkpoint is not None
                and current_height != expected_checkpoint
            ):
                raise ReorgRecoveryError(
                    "Checkpoint changed since reorganization "
                    "detection."
                )

            if ancestor_block > current_height:
                raise ReorgRecoveryError(
                    "Ancestor cannot be above the checkpoint."
                )

            ancestor = await self.canonical_service.get_block(
                chain_id,
                ancestor_block,
            )

            if ancestor is None:
                raise ReorgRecoveryError(
                    "Common ancestor is missing from "
                    "canonical block history."
                )

            if (
                expected_ancestor_hash is not None
                and ancestor.block_hash.lower()
                != expected_ancestor_hash.lower()
            ):
                raise ReorgRecoveryError(
                    "Ancestor hash does not match the "
                    "expected canonical hash."
                )

            if ancestor_block == current_height:
                return ReorgRollbackResult(
                    chain_id=chain_id,
                    previous_checkpoint=current_height,
                    restored_checkpoint=ancestor_block,
                    deleted_blocks=0,
                )

            # Remove orphaned canonical records.
            deleted = (
                await self.canonical_service.delete_blocks_after(
                    chain_id,
                    ancestor_block,
                )
            )

            # Restore the checkpoint to the common ancestor.
            await self.checkpoint_service.rollback_checkpoint(
                chain_id=chain_id,
                block_number=ancestor_block,
                block_hash=ancestor.block_hash,
            )

            # Commit both operations together.
            await self.session.commit()

            logger.warning(
                "Reorganization rollback completed: "
                "chain=%s, previous=%s, ancestor=%s, "
                "deleted=%s",
                chain_id,
                current_height,
                ancestor_block,
                deleted,
            )

            return ReorgRollbackResult(
                chain_id=chain_id,
                previous_checkpoint=current_height,
                restored_checkpoint=ancestor_block,
                deleted_blocks=deleted,
            )

        except BaseException:
            await self.session.rollback()
            raise
