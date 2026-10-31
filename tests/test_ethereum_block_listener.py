
import asyncio

import pytest

from app.events.engine import EventEngine
from app.events.schemas import EventType
from app.events.subscribers.ethereum_blocks import (
    EthereumBlockListener,
)


class FakeEthereumProvider:
    def __init__(self, block_number: int = 100):
        self.block_number = block_number
        self.should_fail = False

    async def get_block_number(self) -> int:
        if self.should_fail:
            raise ConnectionError("RPC temporarily unavailable.")

        return self.block_number


def create_listener(
    provider=None,
    start_from_block=None,
    poll_interval=0.01,
):
    provider = provider or FakeEthereumProvider()
    engine = EventEngine()

    listener = EthereumBlockListener(
        provider=provider,
        event_engine=engine,
        chain_id=1,
        poll_interval=poll_interval,
        start_from_block=start_from_block,
    )

    return listener, engine, provider


@pytest.mark.asyncio
async def test_listener_initializes_at_latest_block():
    listener, _, _ = create_listener()

    count = await listener.poll_once()

    assert count == 0
    assert listener.last_processed_block == 100


@pytest.mark.asyncio
async def test_listener_detects_new_block():
    listener, engine, provider = create_listener()
    received = []

    async def handler(event):
        received.append(event)

    engine.subscribe(EventType.BLOCK_MINED, handler)

    await listener.poll_once()

    provider.block_number = 101

    count = await listener.poll_once()

    assert count == 1
    assert len(received) == 1
    assert received[0].payload["block_number"] == 101
    assert received[0].chain_id == 1


@pytest.mark.asyncio
async def test_listener_detects_multiple_blocks():
    listener, engine, provider = create_listener(
        start_from_block=100
    )
    received = []

    async def handler(event):
        received.append(event.payload["block_number"])

    engine.subscribe(EventType.BLOCK_MINED, handler)

    provider.block_number = 103

    count = await listener.poll_once()

    assert count == 3
    assert received == [101, 102, 103]
    assert listener.last_processed_block == 103


@pytest.mark.asyncio
async def test_listener_does_not_duplicate_blocks():
    listener, engine, provider = create_listener(
        start_from_block=100
    )
    received = []

    async def handler(event):
        received.append(event.payload["block_number"])

    engine.subscribe(EventType.BLOCK_MINED, handler)

    provider.block_number = 101

    await listener.poll_once()
    await listener.poll_once()

    assert received == [101]


@pytest.mark.asyncio
async def test_listener_handles_older_block_number():
    listener, _, provider = create_listener(
        start_from_block=105
    )

    provider.block_number = 103

    count = await listener.poll_once()

    assert count == 0
    assert listener.last_processed_block == 105


@pytest.mark.asyncio
async def test_listener_recovers_after_rpc_failure():
    listener, _, provider = create_listener(
        start_from_block=100
    )

    provider.should_fail = True

    with pytest.raises(ConnectionError):
        await listener.poll_once()

    assert listener.last_processed_block == 100

    provider.should_fail = False
    provider.block_number = 101

    count = await listener.poll_once()

    assert count == 1
    assert listener.last_processed_block == 101


@pytest.mark.asyncio
async def test_listener_start_and_stop():
    listener, _, _ = create_listener()

    task = asyncio.create_task(listener.run())

    try:
        await asyncio.wait_for(
            wait_until_running(listener),
            timeout=1.0,
        )

        assert listener.is_running is True
    finally:
        listener.stop()
        await asyncio.wait_for(task, timeout=1.0)

    assert listener.is_running is False


async def wait_until_running(listener):
    while not listener.is_running:
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_listener_rejects_invalid_block_number():
    provider = FakeEthereumProvider(block_number=-1)
    listener, _, _ = create_listener(provider=provider)

    with pytest.raises(ValueError):
        await listener.poll_once()


def test_listener_rejects_invalid_poll_interval():
    with pytest.raises(ValueError):
        create_listener(poll_interval=0)


def test_listener_rejects_invalid_chain_id():
    with pytest.raises(ValueError):
        EthereumBlockListener(
            provider=FakeEthereumProvider(),
            event_engine=EventEngine(),
            chain_id=0,
        )


def test_listener_rejects_negative_start_block():
    with pytest.raises(ValueError):
        create_listener(start_from_block=-1)
