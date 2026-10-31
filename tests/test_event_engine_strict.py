
import pytest

from app.events.engine import EventEngine
from app.events.schemas import BlockchainEvent, EventType


def make_block_event() -> BlockchainEvent:
    return BlockchainEvent(
        event_type=EventType.BLOCK_MINED,
        source="test",
        chain_id=1,
        payload={"block_number": 100},
    )


@pytest.mark.asyncio
async def test_default_mode_preserves_existing_behavior():
    engine = EventEngine()

    async def failing_handler(event):
        raise RuntimeError("RPC unavailable")

    engine.subscribe(
        EventType.BLOCK_MINED,
        failing_handler,
    )

    await engine.publish(make_block_event())


@pytest.mark.asyncio
async def test_strict_mode_propagates_failure():
    engine = EventEngine()

    async def failing_handler(event):
        raise RuntimeError("RPC unavailable")

    engine.subscribe(
        EventType.BLOCK_MINED,
        failing_handler,
    )

    with pytest.raises(ExceptionGroup) as exc_info:
        await engine.publish(
            make_block_event(),
            raise_on_error=True,
        )

    assert len(exc_info.value.exceptions) == 1
    assert isinstance(
        exc_info.value.exceptions[0],
        RuntimeError,
    )


@pytest.mark.asyncio
async def test_strict_mode_succeeds_when_handlers_succeed():
    engine = EventEngine()
    received = []

    async def successful_handler(event):
        received.append(event.payload["block_number"])

    engine.subscribe(
        EventType.BLOCK_MINED,
        successful_handler,
    )

    await engine.publish(
        make_block_event(),
        raise_on_error=True,
    )

    assert received == [100]


@pytest.mark.asyncio
async def test_strict_mode_waits_for_all_handlers():
    engine = EventEngine()
    received = []

    async def first_handler(event):
        received.append("first")

    async def second_handler(event):
        received.append("second")

    engine.subscribe(EventType.BLOCK_MINED, first_handler)
    engine.subscribe(EventType.BLOCK_MINED, second_handler)

    await engine.publish(
        make_block_event(),
        raise_on_error=True,
    )

    assert sorted(received) == ["first", "second"]
