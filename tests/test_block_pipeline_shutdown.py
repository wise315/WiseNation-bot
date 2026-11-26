
import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from app.events.processors.block_pipeline import BlockEventPipeline


def build_pipeline():
    return BlockEventPipeline(
        activity_provider=Mock(),
        nft_processor=Mock(),
        event_engine=Mock(),
        chain_id=1,
    )


@pytest.mark.asyncio
async def test_shutdown_unsubscribes_pipeline():
    pipeline = build_pipeline()

    pipeline.start()

    assert pipeline._subscribed is True

    await pipeline.shutdown()

    assert pipeline._subscribed is False

    pipeline.event_engine.unsubscribe.assert_called_once()


@pytest.mark.asyncio
async def test_shutdown_rejects_new_blocks():
    pipeline = build_pipeline()

    await pipeline.shutdown()

    with pytest.raises(
        RuntimeError,
        match="Block pipeline is shutting down",
    ):
        await pipeline.process_block(100)


@pytest.mark.asyncio
async def test_shutdown_waits_for_inflight_processing():
    pipeline = build_pipeline()

    processing_started = asyncio.Event()
    allow_completion = asyncio.Event()

    async def process(block_number):
        processing_started.set()

        await allow_completion.wait()

        return 1

    pipeline._process_block = AsyncMock(
        side_effect=process
    )

    processing_task = asyncio.create_task(
        pipeline.process_block(100)
    )

    await asyncio.wait_for(
        processing_started.wait(),
        timeout=2,
    )

    shutdown_task = asyncio.create_task(
        pipeline.shutdown()
    )

    try:
        await asyncio.sleep(0)

        assert not shutdown_task.done()

        allow_completion.set()

        result = await asyncio.wait_for(
            processing_task,
            timeout=2,
        )

        await asyncio.wait_for(
            shutdown_task,
            timeout=2,
        )

        assert result == 1
        assert pipeline._inflight == {}

    finally:
        allow_completion.set()

        await asyncio.gather(
            processing_task,
            shutdown_task,
            return_exceptions=True,
        )


@pytest.mark.asyncio
async def test_shutdown_drains_shielded_task_after_caller_cancellation():
    pipeline = build_pipeline()

    processing_started = asyncio.Event()
    allow_completion = asyncio.Event()
    processing_completed = asyncio.Event()

    async def process(block_number):
        processing_started.set()

        await allow_completion.wait()

        processing_completed.set()

        return 1

    pipeline._process_block = AsyncMock(
        side_effect=process
    )

    caller_task = asyncio.create_task(
        pipeline.process_block(100)
    )

    await asyncio.wait_for(
        processing_started.wait(),
        timeout=2,
    )

    caller_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await caller_task

    # Cancelling the caller must not cancel the
    # shielded block-processing task.
    assert not processing_completed.is_set()
    assert 100 in pipeline._inflight

    shutdown_task = asyncio.create_task(
        pipeline.shutdown()
    )

    try:
        await asyncio.sleep(0)

        assert not shutdown_task.done()

        allow_completion.set()

        await asyncio.wait_for(
            shutdown_task,
            timeout=2,
        )

        assert processing_completed.is_set()
        assert pipeline._inflight == {}

    finally:
        allow_completion.set()

        await asyncio.gather(
            shutdown_task,
            return_exceptions=True,
        )


@pytest.mark.asyncio
async def test_shutdown_is_idempotent():
    pipeline = build_pipeline()

    pipeline.start()

    await pipeline.shutdown()
    await pipeline.shutdown()
    await pipeline.shutdown()

    pipeline.event_engine.unsubscribe.assert_called_once()

    assert pipeline._subscribed is False
    assert pipeline._inflight == {}


@pytest.mark.asyncio
async def test_pipeline_cannot_restart_after_shutdown():
    pipeline = build_pipeline()

    await pipeline.shutdown()

    with pytest.raises(
        RuntimeError,
        match="Block pipeline is shutting down",
    ):
        pipeline.start()

    pipeline.event_engine.subscribe.assert_not_called()
