import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.events.processors.block_pipeline import BlockEventPipeline


BLOCK_HASH = "0x" + "a" * 64
PARENT_HASH = "0x" + "b" * 64


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


def build_pipeline(
    operations,
    *,
    persistence_error=None,
    commit_error=None,
    publish_error=None,
):
    session = Mock()

    async def commit():
        operations.append("commit")

        if commit_error is not None:
            raise commit_error

    async def rollback():
        operations.append("rollback")

    session.commit = AsyncMock(side_effect=commit)
    session.rollback = AsyncMock(side_effect=rollback)

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

    async def persist(events, block_hash):
        operations.append("persist")

        assert block_hash == BLOCK_HASH

        if persistence_error is not None:
            raise persistence_error

        return list(events)

    nft_event_service.save_new_events = AsyncMock(
        side_effect=persist
    )

    activity_provider = Mock()

    activity_provider.get_block_metadata = AsyncMock(
        return_value=(BLOCK_HASH, PARENT_HASH)
    )

    activity_provider.get_block_logs = AsyncMock(
        return_value=[Mock()]
    )

    nft_processor = Mock()

    decoded_event = Mock()

    nft_processor.decode_logs = Mock(
        return_value=[decoded_event]
    )

    async def publish(events):
        operations.append("publish")

        assert events == [decoded_event]

        if publish_error is not None:
            raise publish_error

        return len(events)

    nft_processor.publish_events = AsyncMock(
        side_effect=publish
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

    return pipeline, session, nft_processor


@pytest.mark.asyncio
async def test_nft_events_are_persisted_before_commit():
    operations = []

    pipeline, session, nft_processor = build_pipeline(
        operations
    )

    count = await pipeline.process_block(100)

    assert count == 1

    assert operations == [
        "persist",
        "canonical",
        "checkpoint",
        "commit",
        "publish",
    ]

    session.rollback.assert_not_awaited()
    nft_processor.publish_events.assert_awaited_once()


@pytest.mark.asyncio
async def test_persistence_failure_prevents_commit_and_publish():
    operations = []

    pipeline, session, nft_processor = build_pipeline(
        operations,
        persistence_error=RuntimeError("persistence failed"),
    )

    with pytest.raises(
        RuntimeError,
        match="persistence failed",
    ):
        await pipeline.process_block(100)

    assert operations == [
        "persist",
        "rollback",
    ]

    session.commit.assert_not_awaited()
    nft_processor.publish_events.assert_not_awaited()


@pytest.mark.asyncio
async def test_commit_failure_prevents_publish():
    operations = []

    pipeline, session, nft_processor = build_pipeline(
        operations,
        commit_error=RuntimeError("commit failed"),
    )

    with pytest.raises(
        RuntimeError,
        match="commit failed",
    ):
        await pipeline.process_block(100)

    assert operations == [
        "persist",
        "canonical",
        "checkpoint",
        "commit",
        "rollback",
    ]

    nft_processor.publish_events.assert_not_awaited()


@pytest.mark.asyncio
async def test_publication_failure_does_not_rollback_committed_data():
    operations = []

    pipeline, session, _ = build_pipeline(
        operations,
        publish_error=RuntimeError("subscriber failed"),
    )

    with pytest.raises(
        RuntimeError,
        match="subscriber failed",
    ):
        await pipeline.process_block(100)

    assert operations == [
        "persist",
        "canonical",
        "checkpoint",
        "commit",
        "publish",
    ]

    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_replayed_block_does_not_publish_duplicate_events():
    operations = []

    pipeline, session, nft_processor = build_pipeline(
        operations
    )

    nft_event_service = pipeline.nft_event_service

    saved_identities = set()

    async def persist_only_new(events, block_hash):
        operations.append("persist")

        new_events = []

        for event in events:
            identity = (
                block_hash,
                id(event),
            )

            if identity not in saved_identities:
                saved_identities.add(identity)
                new_events.append(event)

        return new_events

    nft_event_service.save_new_events = AsyncMock(
        side_effect=persist_only_new
    )

    first_count = await pipeline.process_block(100)

    # Allow the pipeline's scheduled cleanup callback to run.
    # This avoids manually accessing a task that may
    # already have been removed.
    await asyncio.sleep(0)
    
    # Wait until the completed task has been removed.
    # If it is still present, explicitly clean up
    # the task using a safe lookup.
    task = pipeline._inflight.get(100)
    
    if task is not None:
        await pipeline._cleanup_task(100, task)
        
    # Replay the same block.
    second_count = await pipeline.process_block(100)


    assert first_count == 1
    assert second_count == 0

    nonempty_publications = [
        call
        for call in nft_processor.publish_events.await_args_list
        if call.args[0]
    ]

    assert len(nonempty_publications) == 1
    assert session.commit.await_count == 2
