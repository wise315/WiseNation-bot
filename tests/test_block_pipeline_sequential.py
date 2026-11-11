
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.events.processors.block_pipeline import BlockEventPipeline


@pytest.fixture
def pipeline():
    provider = MagicMock()
    provider.get_block_logs = AsyncMock(return_value=[])

    processor = MagicMock()
    processor.process_logs = AsyncMock(return_value=0)

    return BlockEventPipeline(
        activity_provider=provider,
        nft_processor=processor,
        event_engine=MagicMock(),
        chain_id=1,
    )


@pytest.mark.asyncio
async def test_different_blocks_do_not_overlap(pipeline):
    active = 0
    maximum_active = 0

    async def process(block_number):
        nonlocal active, maximum_active

        active += 1
        maximum_active = max(maximum_active, active)

        await asyncio.sleep(0.02)

        active -= 1
        return 1

    pipeline._process_block = process

    results = await asyncio.gather(
        pipeline.process_block(100),
        pipeline.process_block(101),
        pipeline.process_block(102),
    )

    assert results == [1, 1, 1]
    assert maximum_active == 1


@pytest.mark.asyncio
async def test_duplicate_block_processed_once(pipeline):
    calls = 0

    async def process(block_number):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return 2

    pipeline._process_block = process

    results = await asyncio.gather(
        pipeline.process_block(100),
        pipeline.process_block(100),
        pipeline.process_block(100),
    )

    assert results == [2, 2, 2]
    assert calls == 1


@pytest.mark.asyncio
async def test_processing_continues_after_failure(pipeline):
    async def process(block_number):
        if block_number == 100:
            raise RuntimeError("RPC failure")

        return 3

    pipeline._process_block = process

    with pytest.raises(RuntimeError):
        await pipeline.process_block(100)

    result = await pipeline.process_block(101)

    assert result == 3


@pytest.mark.asyncio
async def test_lock_released_after_failure(pipeline):
    async def process(block_number):
        if block_number == 100:
            raise RuntimeError("Processing failed")

        return 1

    pipeline._process_block = process

    results = await asyncio.gather(
        pipeline.process_block(100),
        pipeline.process_block(101),
        return_exceptions=True,
    )

    assert isinstance(results[0], RuntimeError)
    assert results[1] == 1

