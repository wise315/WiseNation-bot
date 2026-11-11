
import logging
from dataclasses import dataclass
from typing import Protocol

from app.services.canonical_block_service import (
    CanonicalBlockService,
)


logger = logging.getLogger(__name__)


class BlockMetadataProvider(Protocol):
    async def get_block_metadata(
        self,
        block_number: int,
    ) -> tuple[str, str]:
        ...


class ReorgDetectionError(Exception):
    """Cannot safely determine the common ancestor."""


@dataclass(frozen=True)
class ReorgDetectionResult:
    chain_id: int
    checked_from_block: int
    common_ancestor: int
    orphaned_block_numbers: tuple[int, ...]

    @property
    def reorg_depth(self) -> int:
        return len(self.orphaned_block_numbers)


class BlockReorgDetector:
    def __init__(
        self,
        canonical_service: CanonicalBlockService,
        activity_provider: BlockMetadataProvider,
        chain_id: int = 1,
        max_reorg_depth: int = 64,
    ) -> None:
        if (
            isinstance(chain_id, bool)
            or not isinstance(chain_id, int)
            or chain_id <= 0
        ):
            raise ValueError("chain_id must be positive.")

        if (
            isinstance(max_reorg_depth, bool)
            or not isinstance(max_reorg_depth, int)
            or max_reorg_depth < 1
        ):
            raise ValueError(
                "max_reorg_depth must be a positive integer."
            )

        self.canonical_service = canonical_service
        self.activity_provider = activity_provider
        self.chain_id = chain_id
        self.max_reorg_depth = max_reorg_depth

    async def find_common_ancestor(
        self,
        from_block: int,
    ) -> ReorgDetectionResult:
        if (
            isinstance(from_block, bool)
            or not isinstance(from_block, int)
            or from_block < 0
        ):
            raise ValueError(
                "from_block must be a non-negative integer."
            )

        orphaned = []

        for offset in range(self.max_reorg_depth + 1):
            block_number = from_block - offset

            if block_number < 0:
                break

            stored = await self.canonical_service.get_block(
                chain_id=self.chain_id,
                block_number=block_number,
            )

            if stored is None:
                raise ReorgDetectionError(
                    f"No stored canonical block at height "
                    f"{block_number}. Cannot establish ancestry."
                )

            current_hash, _ = (
                await self.activity_provider.get_block_metadata(
                    block_number
                )
            )

            if stored.block_hash.lower() == current_hash.lower():
                logger.info(
                    "Common ancestor found at block %s",
                    block_number,
                )

                return ReorgDetectionResult(
                    chain_id=self.chain_id,
                    checked_from_block=from_block,
                    common_ancestor=block_number,
                    orphaned_block_numbers=tuple(orphaned),
                )

            if offset == self.max_reorg_depth:
                break

            orphaned.append(block_number)

        raise ReorgDetectionError(
            "Common ancestor not found within the configured "
            f"reorganization depth of {self.max_reorg_depth}."
        )
