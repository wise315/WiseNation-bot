
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.events.processors.block_pipeline import BlockEventPipeline

from unittest.mock import AsyncMock, Mock, call

def test_nft_persistence_requires_shared_session():
    shared_session = object()
    different_session = object()

    checkpoint_service = SimpleNamespace(
        session=shared_session
    )

    canonical_service = SimpleNamespace(
        session=shared_session
    )

    nft_event_service = SimpleNamespace(
        session=different_session
    )

    with pytest.raises(
        ValueError,
        match="same database session",
    ):
        BlockEventPipeline(
            activity_provider=Mock(),
            nft_processor=Mock(),
            event_engine=Mock(),
            chain_id=1,
            checkpoint_service=checkpoint_service,
            canonical_block_service=canonical_service,
            nft_event_service=nft_event_service,
        )

@pytest.mark.asyncio
async def test_nft_events_are_persisted_before_commit():
    operations = []

    session = Mock()
    session.commit = AsyncMock(
        side_effect=lambda: operations.append("commit")
    )
    session.rollback = AsyncMock()

    checkpoint_service = Mock()
    checkpoint_service.session = session
    checkpoint_service.save_checkpoint = AsyncMock(
        side_effect=lambda **kwargs: operations.append("checkpoint")
    )

    canonical_service = Mock()
    canonical_service.session = session
    canonical_service.get_block = AsyncMock(return_value=None)
    canonical_service.save_block = AsyncMock(
        side_effect=lambda **kwargs: operations.append("canonical")
    )

    nft_event_service = Mock()
    nft_event_service.session = session
    nft_event_service.save_events = AsyncMock(
        side_effect=lambda *args, **kwargs: operations.append("persist")
    )

    activity_provider = Mock()
    activity_provider.get_block_metadata = AsyncMock(
        return_value=("0x" + "a" * 64, "0x" + "b" * 64)
    )
    activity_provider.get_block_logs = AsyncMock(
        return_value=[Mock()]
    )

    nft_processor = Mock()
    nft_processor.process_logs = AsyncMock(
        side_effect=lambda logs: operations.append("publish") or 1
    )

    pipeline = BlockEventPipeline(
        activity_provider=activity_provider,
        nft_processor=nft_processor,
        event_engine=Mock(),
        chain_id=1,
        checkpoint_service=checkpoint_service,
        canonical_block_service=canonical_service,
        nft_event_service=nft_event_service,
    )

    await pipeline.process_block(100)

    assert "persist" in operations
    assert operations.index("persist") < operations.index("commit")
    assert operations.index("commit") < operations.index("publish")
