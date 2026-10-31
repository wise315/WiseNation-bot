
import pytest
from pydantic import ValidationError

from app.events.engine import EventEngine
from app.events.schemas import BlockchainEvent, EventType


def make_event() -> BlockchainEvent:
    return BlockchainEvent(
        event_type=EventType.NFT_SALE,
        source="opensea",
        chain_id=1,
        payload={
            "contract_address": "0x123",
            "token_id": "42",
        },
    )


def test_event_creation():
    event = make_event()

    assert event.event_type == EventType.NFT_SALE
    assert event.chain_id == 1
    assert event.payload["token_id"] == "42"
    assert event.event_id is not None
    assert event.timestamp.tzinfo is not None


def test_event_requires_valid_chain_id():
    with pytest.raises(ValidationError):
        BlockchainEvent(
            event_type=EventType.NFT_SALE,
            source="test",
            chain_id=0,
        )


@pytest.mark.asyncio
async def test_event_dispatch():
    engine = EventEngine()
    received = []

    async def handler(event):
        received.append(event)

    engine.subscribe(EventType.NFT_SALE, handler)

    event = make_event()
    await engine.publish(event)

    assert received == [event]


@pytest.mark.asyncio
async def test_multiple_subscribers():
    engine = EventEngine()
    received = []

    async def first(event):
        received.append("first")

    async def second(event):
        received.append("second")

    engine.subscribe(EventType.NFT_SALE, first)
    engine.subscribe(EventType.NFT_SALE, second)

    await engine.publish(make_event())

    assert sorted(received) == ["first", "second"]
    assert engine.subscriber_count(EventType.NFT_SALE) == 2


@pytest.mark.asyncio
async def test_event_type_filtering():
    engine = EventEngine()
    received = []

    async def handler(event):
        received.append(event)

    engine.subscribe(EventType.NFT_TRANSFER, handler)

    await engine.publish(make_event())

    assert received == []


@pytest.mark.asyncio
async def test_unsubscribe():
    engine = EventEngine()
    received = []

    async def handler(event):
        received.append(event)

    engine.subscribe(EventType.NFT_SALE, handler)
    engine.unsubscribe(EventType.NFT_SALE, handler)

    await engine.publish(make_event())

    assert received == []
    assert engine.subscriber_count(EventType.NFT_SALE) == 0


@pytest.mark.asyncio
async def test_handler_failure_does_not_block_others():
    engine = EventEngine()
    received = []

    async def failing_handler(event):
        raise RuntimeError("Simulated handler failure")

    async def working_handler(event):
        received.append(event)

    engine.subscribe(EventType.NFT_SALE, failing_handler)
    engine.subscribe(EventType.NFT_SALE, working_handler)

    event = make_event()
    await engine.publish(event)

    assert received == [event]


@pytest.mark.asyncio
async def test_duplicate_subscription_is_ignored():
    engine = EventEngine()
    received = []

    async def handler(event):
        received.append(event)

    engine.subscribe(EventType.NFT_SALE, handler)
    engine.subscribe(EventType.NFT_SALE, handler)

    await engine.publish(make_event())

    assert len(received) == 1
    assert engine.subscriber_count(EventType.NFT_SALE) == 1


@pytest.mark.asyncio
async def test_publish_without_subscribers():
    engine = EventEngine()

    await engine.publish(make_event())


@pytest.mark.asyncio
async def test_publish_rejects_invalid_event():
    engine = EventEngine()

    with pytest.raises(TypeError):
        await engine.publish({"event_type": "nft.sale"})
