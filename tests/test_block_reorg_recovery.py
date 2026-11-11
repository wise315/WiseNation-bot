
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.block_reorg_recovery import (
    BlockReorgRecoveryService,
    ReorgRecoveryError,
)


HASH_A = "0x" + "a" * 64
HASH_B = "0x" + "b" * 64


@pytest.fixture
def recovery_setup():
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    canonical = MagicMock()
    canonical.session = session
    canonical.get_block = AsyncMock()
    canonical.delete_blocks_after = AsyncMock(
        return_value=2
    )

    checkpoint = MagicMock()
    checkpoint.session = session
    checkpoint.get_checkpoint = AsyncMock()
    checkpoint.rollback_checkpoint = AsyncMock()

    stored_checkpoint = MagicMock()
    stored_checkpoint.last_processed_block = 103

    ancestor = MagicMock()
    ancestor.block_number = 101
    ancestor.block_hash = HASH_A

    checkpoint.get_checkpoint.return_value = (
        stored_checkpoint
    )
    canonical.get_block.return_value = ancestor

    service = BlockReorgRecoveryService(
        canonical_service=canonical,
        checkpoint_service=checkpoint,
    )

    return service, canonical, checkpoint, session


@pytest.mark.asyncio
async def test_successful_rollback(recovery_setup):
    service, canonical, checkpoint, session = (
        recovery_setup
    )

    result = await service.rollback_to_ancestor(
        chain_id=1,
        ancestor_block=101,
        expected_checkpoint=103,
        expected_ancestor_hash=HASH_A,
    )

    assert result.previous_checkpoint == 103
    assert result.restored_checkpoint == 101
    assert result.deleted_blocks == 2

    canonical.delete_blocks_after.assert_awaited_once_with(
        1, 101
    )

    checkpoint.rollback_checkpoint.assert_awaited_once_with(
        chain_id=1,
        block_number=101,
        block_hash=HASH_A,
    )

    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_checkpoint(recovery_setup):
    service, canonical, checkpoint, session = (
        recovery_setup
    )

    checkpoint.get_checkpoint.return_value = None

    with pytest.raises(ReorgRecoveryError):
        await service.rollback_to_ancestor(1, 101)

    canonical.delete_blocks_after.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_checkpoint_changed(recovery_setup):
    service, canonical, checkpoint, session = (
        recovery_setup
    )

    with pytest.raises(
        ReorgRecoveryError,
        match="Checkpoint changed",
    ):
        await service.rollback_to_ancestor(
            1, 101, expected_checkpoint=104
        )

    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_ancestor_above_checkpoint(recovery_setup):
    service, canonical, checkpoint, session = (
        recovery_setup
    )

    with pytest.raises(ReorgRecoveryError):
        await service.rollback_to_ancestor(1, 105)

    canonical.delete_blocks_after.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_ancestor(recovery_setup):
    service, canonical, checkpoint, session = (
        recovery_setup
    )

    canonical.get_block.return_value = None

    with pytest.raises(ReorgRecoveryError):
        await service.rollback_to_ancestor(1, 101)

    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_ancestor_hash_mismatch(recovery_setup):
    service, canonical, checkpoint, session = (
        recovery_setup
    )

    with pytest.raises(
        ReorgRecoveryError,
        match="Ancestor hash",
    ):
        await service.rollback_to_ancestor(
            1,
            101,
            expected_ancestor_hash=HASH_B,
        )

    canonical.delete_blocks_after.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_failure_rolls_back(recovery_setup):
    service, canonical, checkpoint, session = (
        recovery_setup
    )

    canonical.delete_blocks_after.side_effect = (
        RuntimeError("Database delete failed")
    )

    with pytest.raises(RuntimeError):
        await service.rollback_to_ancestor(1, 101)

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_checkpoint_failure_rolls_back(recovery_setup):
    service, canonical, checkpoint, session = (
        recovery_setup
    )

    checkpoint.rollback_checkpoint.side_effect = (
        RuntimeError("Checkpoint update failed")
    )

    with pytest.raises(RuntimeError):
        await service.rollback_to_ancestor(1, 101)

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_commit_failure_rolls_back(recovery_setup):
    service, canonical, checkpoint, session = (
        recovery_setup
    )

    session.commit.side_effect = RuntimeError(
        "Commit failed"
    )

    with pytest.raises(RuntimeError):
        await service.rollback_to_ancestor(1, 101)

    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_noop_when_already_at_ancestor(recovery_setup):
    service, canonical, checkpoint, session = (
        recovery_setup
    )

    checkpoint.get_checkpoint.return_value.last_processed_block = (
        101
    )

    result = await service.rollback_to_ancestor(1, 101)

    assert result.deleted_blocks == 0
    canonical.delete_blocks_after.assert_not_awaited()
    checkpoint.rollback_checkpoint.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_chain_id(recovery_setup):
    service, canonical, checkpoint, session = (
        recovery_setup
    )

    with pytest.raises(ValueError):
        await service.rollback_to_ancestor(0, 101)


@pytest.mark.asyncio
async def test_invalid_ancestor(recovery_setup):
    service, canonical, checkpoint, session = (
        recovery_setup
    )

    with pytest.raises(ValueError):
        await service.rollback_to_ancestor(1, -1)


@pytest.mark.asyncio
async def test_invalid_expected_checkpoint(recovery_setup):
    service, canonical, checkpoint, session = (
        recovery_setup
    )

    with pytest.raises(ValueError):
        await service.rollback_to_ancestor(
            1, 101, expected_checkpoint=-1
        )


@pytest.mark.asyncio
async def test_invalid_expected_hash(recovery_setup):
    service, canonical, checkpoint, session = (
        recovery_setup
    )

    with pytest.raises(ValueError):
        await service.rollback_to_ancestor(
            1, 101, expected_ancestor_hash="invalid"
        )


def test_different_sessions_rejected(recovery_setup):
    service, canonical, checkpoint, session = (
        recovery_setup
    )

    canonical.session = MagicMock()

    with pytest.raises(ValueError):
        BlockReorgRecoveryService(
            canonical_service=canonical,
            checkpoint_service=checkpoint,
        )
