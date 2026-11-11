
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.events.processors.block_pipeline import BlockEventPipeline
from app.services.canonical_block_service import (
    CanonicalBlockConflictError,
)


HASH_A = "0x" + "a" * 64
HASH_B = "0x" + "b" * 64
HASH_C = "0x" + "c" * 64


@pytest.fixture
def setup_pipeline():
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    checkpoint = MagicMock()
    checkpoint.session = session
    checkpoint.save_checkpoint = AsyncMock()

    canonical = MagicMock()
    canonical.session = session
    canonical.get_block = AsyncMock(return_value=None)
    canonical.save_block = AsyncMock()

    provider = MagicMock()
    provider.get_block_metadata = AsyncMock(
        return_value={
            "block_hash": HASH_B,
            "parent_hash": HASH_A,
        }
    )
    provider.get_block_logs = AsyncMock(return_value=[])

    processor = MagicMock()
    processor.process_logs = AsyncMock(return_value=0)

    pipeline = BlockEventPipeline(
        activity_provider=provider,
        nft_processor=processor,
        event_engine=MagicMock(),
        chain_id=1,
        checkpoint_service=checkpoint,
        canonical_block_service=canonical,
    )

    return pipeline, provider, processor, checkpoint, canonical, session


@pytest.mark.asyncio
async def test_block_saved_with_checkpoint(setup_pipeline):
    pipeline, provider, processor, checkpoint, canonical, session = (
        setup_pipeline
    )

    count = await pipeline.process_block(100)

    assert count == 0
    canonical.save_block.assert_awaited_once_with(
        chain_id=1,
        block_number=100,
        block_hash=HASH_B,
        parent_hash=HASH_A,
    )
    checkpoint.save_checkpoint.assert_awaited_once_with(
        chain_id=1,
        block_number=100,
        block_hash=HASH_B,
    )
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_conflicting_block_rejected(setup_pipeline):
    pipeline, provider, processor, checkpoint, canonical, session = (
        setup_pipeline
    )

    existing = MagicMock()
    existing.block_hash = HASH_C
    existing.parent_hash = HASH_A

    async def lookup(chain_id, block_number):
        return existing if block_number == 100 else None

    canonical.get_block.side_effect = lookup

    with pytest.raises(CanonicalBlockConflictError):
        await pipeline.process_block(100)

    processor.process_logs.assert_not_awaited()
    checkpoint.save_checkpoint.assert_not_awaited()
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_parent_hash_mismatch(setup_pipeline):
    pipeline, provider, processor, checkpoint, canonical, session = (
        setup_pipeline
    )

    previous = MagicMock()
    previous.block_hash = HASH_C

    async def lookup(chain_id, block_number):
        return previous if block_number == 99 else None

    canonical.get_block.side_effect = lookup

    with pytest.raises(CanonicalBlockConflictError):
        await pipeline.process_block(100)

    processor.process_logs.assert_not_awaited()
    canonical.save_block.assert_not_awaited()
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_processing_failure_rolls_back(setup_pipeline):
    pipeline, provider, processor, checkpoint, canonical, session = (
        setup_pipeline
    )

    processor.process_logs.side_effect = RuntimeError(
        "NFT processing failed"
    )

    with pytest.raises(RuntimeError):
        await pipeline.process_block(100)

    canonical.save_block.assert_not_awaited()
    checkpoint.save_checkpoint.assert_not_awaited()
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_commit_failure_rolls_back(setup_pipeline):
    pipeline, provider, processor, checkpoint, canonical, session = (
        setup_pipeline
    )

    session.commit.side_effect = RuntimeError(
        "Database commit failed"
    )

    with pytest.raises(RuntimeError):
        await pipeline.process_block(100)

    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_matching_existing_block(setup_pipeline):
    pipeline, provider, processor, checkpoint, canonical, session = (
        setup_pipeline
    )

    existing = MagicMock()
    existing.block_hash = HASH_B
    existing.parent_hash = HASH_A

    async def lookup(chain_id, block_number):
        return existing if block_number == 100 else None

    canonical.get_block.side_effect = lookup

    await pipeline.process_block(100)

    canonical.save_block.assert_awaited_once()
    session.commit.assert_awaited_once()


def test_different_sessions_rejected(setup_pipeline):
    pipeline, provider, processor, checkpoint, canonical, session = (
        setup_pipeline
    )

    canonical.session = MagicMock()

    with pytest.raises(ValueError):
        BlockEventPipeline(
            activity_provider=provider,
            nft_processor=processor,
            event_engine=MagicMock(),
            checkpoint_service=checkpoint,
            canonical_block_service=canonical,
        )

@pytest.mark.asyncio
async def test_block_metadata_tuple_supported(setup_pipeline):
    (
        pipeline,
        provider,
        processor,
        checkpoint,
        canonical,
        session,
    ) = setup_pipeline

    # Match the real EthereumActivityProvider return format.
    provider.get_block_metadata.return_value = (
        HASH_B,
        HASH_A,
    )

    await pipeline.process_block(100)

    canonical.save_block.assert_awaited_once_with(
        chain_id=1,
        block_number=100,
        block_hash=HASH_B,
        parent_hash=HASH_A,
    )

    checkpoint.save_checkpoint.assert_awaited_once_with(
        chain_id=1,
        block_number=100,
        block_hash=HASH_B,
    )

    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
