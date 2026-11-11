
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.models.canonical_block import CanonicalBlock
from app.services.canonical_block_service import (
    CanonicalBlockConflictError,
    CanonicalBlockService,
)


HASH_A = "0x" + "a" * 64
HASH_B = "0x" + "b" * 64
HASH_C = "0x" + "c" * 64


@pytest.fixture
def session():
    mock = MagicMock()
    mock.execute = AsyncMock()
    mock.flush = AsyncMock()
    mock.commit = AsyncMock()
    return mock


@pytest.fixture
def service(session):
    return CanonicalBlockService(session)


@pytest.mark.asyncio
async def test_get_block_returns_none(service, session):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    block = await service.get_block(1, 100)

    assert block is None


@pytest.mark.asyncio
async def test_save_new_block(service, session):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    block = await service.save_block(
        chain_id=1,
        block_number=100,
        block_hash=HASH_A,
        parent_hash=HASH_B,
    )

    assert isinstance(block, CanonicalBlock)
    assert block.block_number == 100
    assert block.block_hash == HASH_A

    session.add.assert_called_once_with(block)
    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_save_existing_matching_block(service, session):
    existing = CanonicalBlock(
        chain_id=1,
        block_number=100,
        block_hash=HASH_A,
        parent_hash=HASH_B,
    )

    result = MagicMock()
    result.scalar_one_or_none.return_value = existing
    session.execute.return_value = result

    block = await service.save_block(
        1, 100, HASH_A, HASH_B
    )

    assert block is existing
    session.add.assert_not_called()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_conflicting_block_detected(service, session):
    existing = CanonicalBlock(
        chain_id=1,
        block_number=100,
        block_hash=HASH_A,
        parent_hash=HASH_B,
    )

    result = MagicMock()
    result.scalar_one_or_none.return_value = existing
    session.execute.return_value = result

    with pytest.raises(CanonicalBlockConflictError):
        await service.save_block(
            1, 100, HASH_C, HASH_B
        )

    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_conflicting_parent_detected(service, session):
    existing = CanonicalBlock(
        chain_id=1,
        block_number=100,
        block_hash=HASH_A,
        parent_hash=HASH_B,
    )

    result = MagicMock()
    result.scalar_one_or_none.return_value = existing
    session.execute.return_value = result

    with pytest.raises(CanonicalBlockConflictError):
        await service.save_block(
            1, 100, HASH_A, HASH_C
        )


@pytest.mark.asyncio
async def test_delete_blocks_after(service, session):
    result = MagicMock()
    result.rowcount = 3
    session.execute.return_value = result

    deleted = await service.delete_blocks_after(1, 100)

    assert deleted == 3
    session.execute.assert_awaited_once()
    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_latest_block(service, session):
    latest = CanonicalBlock(
        chain_id=1,
        block_number=105,
        block_hash=HASH_A,
        parent_hash=HASH_B,
    )

    result = MagicMock()
    result.scalar_one_or_none.return_value = latest
    session.execute.return_value = result

    block = await service.get_latest_block(1)

    assert block.block_number == 105


@pytest.mark.asyncio
async def test_invalid_chain_id(service):
    with pytest.raises(ValueError):
        await service.get_block(0, 100)


@pytest.mark.asyncio
async def test_invalid_block_number(service):
    with pytest.raises(ValueError):
        await service.get_block(1, -1)


@pytest.mark.asyncio
async def test_invalid_hash(service):
    with pytest.raises(ValueError):
        await service.save_block(
            1, 100, "invalid", HASH_B
        )


@pytest.mark.asyncio
async def test_non_hex_hash(service):
    with pytest.raises(ValueError):
        await service.save_block(
            1, 100, "0x" + "z" * 64, HASH_B
        )


@pytest.mark.asyncio
async def test_boolean_block_number_rejected(service):
    with pytest.raises(ValueError):
        await service.get_block(1, True)
