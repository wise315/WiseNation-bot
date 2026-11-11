
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.block_reorg_detector import (
    BlockReorgDetector,
    ReorgDetectionError,
)


def block_hash(char: str) -> str:
    return "0x" + char * 64


@pytest.fixture
def setup_detector():
    stored_hashes = {
        100: block_hash("a"),
        101: block_hash("b"),
        102: block_hash("c"),
        103: block_hash("d"),
    }

    current_hashes = {
        100: block_hash("a"),
        101: block_hash("b"),
        102: block_hash("e"),
        103: block_hash("f"),
    }

    canonical = MagicMock()
    provider = MagicMock()

    async def get_stored(chain_id, block_number):
        hash_value = stored_hashes.get(block_number)

        if hash_value is None:
            return None

        block = MagicMock()
        block.block_hash = hash_value
        return block

    async def get_current(block_number):
        return current_hashes[block_number], block_hash("a")

    canonical.get_block = AsyncMock(side_effect=get_stored)
    provider.get_block_metadata = AsyncMock(
        side_effect=get_current
    )

    detector = BlockReorgDetector(
        canonical_service=canonical,
        activity_provider=provider,
        chain_id=1,
        max_reorg_depth=10,
    )

    return detector, canonical, provider, stored_hashes, current_hashes


@pytest.mark.asyncio
async def test_finds_common_ancestor(setup_detector):
    detector, canonical, provider, stored, current = (
        setup_detector
    )

    result = await detector.find_common_ancestor(103)

    assert result.common_ancestor == 101
    assert result.orphaned_block_numbers == (103, 102)
    assert result.reorg_depth == 2
    assert result.chain_id == 1


@pytest.mark.asyncio
async def test_no_reorg_when_hash_matches(setup_detector):
    detector, canonical, provider, stored, current = (
        setup_detector
    )

    current[103] = stored[103]

    result = await detector.find_common_ancestor(103)

    assert result.common_ancestor == 103
    assert result.reorg_depth == 0
    assert result.orphaned_block_numbers == ()


@pytest.mark.asyncio
async def test_single_block_reorg(setup_detector):
    detector, canonical, provider, stored, current = (
        setup_detector
    )

    current[102] = stored[102]

    result = await detector.find_common_ancestor(103)

    assert result.common_ancestor == 102
    assert result.orphaned_block_numbers == (103,)


@pytest.mark.asyncio
async def test_missing_stored_block_raises(setup_detector):
    detector, canonical, provider, stored, current = (
        setup_detector
    )

    del stored[102]

    with pytest.raises(
        ReorgDetectionError,
        match="No stored canonical block",
    ):
        await detector.find_common_ancestor(103)


@pytest.mark.asyncio
async def test_depth_limit_raises(setup_detector):
    detector, canonical, provider, stored, current = (
        setup_detector
    )

    detector.max_reorg_depth = 1

    with pytest.raises(
        ReorgDetectionError,
        match="Common ancestor not found",
    ):
        await detector.find_common_ancestor(103)


@pytest.mark.asyncio
async def test_invalid_start_block(setup_detector):
    detector, canonical, provider, stored, current = (
        setup_detector
    )

    with pytest.raises(ValueError):
        await detector.find_common_ancestor(-1)


@pytest.mark.asyncio
async def test_boolean_start_block_rejected(setup_detector):
    detector, canonical, provider, stored, current = (
        setup_detector
    )

    with pytest.raises(ValueError):
        await detector.find_common_ancestor(True)


@pytest.mark.asyncio
async def test_missing_start_block_raises(setup_detector):
    detector, canonical, provider, stored, current = (
        setup_detector
    )

    del stored[103]

    with pytest.raises(ReorgDetectionError):
        await detector.find_common_ancestor(103)


def test_invalid_chain_id(setup_detector):
    detector, canonical, provider, stored, current = (
        setup_detector
    )

    with pytest.raises(ValueError):
        BlockReorgDetector(
            canonical_service=canonical,
            activity_provider=provider,
            chain_id=0,
        )


def test_invalid_max_depth(setup_detector):
    detector, canonical, provider, stored, current = (
        setup_detector
    )

    with pytest.raises(ValueError):
        BlockReorgDetector(
            canonical_service=canonical,
            activity_provider=provider,
            max_reorg_depth=0,
        )
