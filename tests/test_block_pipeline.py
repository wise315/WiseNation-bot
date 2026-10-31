
import asyncio
from unittest.mock import AsyncMock

import pytest

from app.events.engine import EventEngine
from app.events.processors.block_pipeline import (
    BlockEventPipeline,
)
from app.events.processors.nft_decoder import (
    ERC721_TRANSFER_TOPIC,
    NFTEventDecoder,
    ZERO_ADDRESS,
)
from app.events.processors.nft_processor import NFTEventProcessor
from app.events.schemas import BlockchainEvent, EventType
from app.schemas.blockchain_activity import EthereumContractLog


ALICE = "0x" + "11" * 20
BOB = "0x" + "22" * 20
CONTRACT = "0x" + "33" * 20


def address_topic(address: str) -> str:
    return "0x" + address[2:].lower().zfill(64)


def uint_topic(value: int) -> str:
    return "0x" + value.to_bytes(32, "big").hex()


def make_log(
    token_id: int = 1,
    from_address: str = ALICE,
    to_address: str = BOB,
    block_number: int = 100,
) -> EthereumContractLog:
    return EthereumContractLog(
        transaction_hash="0x" + "aa" * 32,
        block_number=block_number,
        log_index=token_id,
        contract_address=CONTRACT,
        topics=[
            ERC721_TRANSFER_TOPIC,
            address_topic(from_address),
            address_topic(to_address),
            uint_topic(token_id),
        ],
        data="0x",
    )


def make_pipeline(logs=None, chain_id=1):
    engine = EventEngine()

    provider = AsyncMock()
    provider.get_block_logs.return_value = (
        logs if logs is not None else []
    )

    decoder = NFTEventDecoder(chain_id=chain_id)
    processor = NFTEventProcessor(decoder, engine)

    pipeline = BlockEventPipeline(
        activity_provider=provider,
        nft_processor=processor,
        event_engine=engine,
        chain_id=chain_id,
    )

    return pipeline, engine, provider


def make_block_event(block_number=100, chain_id=1):
    return BlockchainEvent(
        event_type=EventType.BLOCK_MINED,
        source="ethereum_rpc",
        chain_id=chain_id,
        payload={"block_number": block_number},
    )


@pytest.mark.asyncio
async def test_pipeline_processes_nft_transfer():
    pipeline, engine, provider = make_pipeline(
        logs=[make_log(token_id=42)]
    )

    received = []

    async def handler(event):
        received.append(event)

    engine.subscribe(EventType.NFT_TRANSFER, handler)

    count = await pipeline.process_block(100)

    assert count == 1
    assert len(received) == 1
    assert received[0].payload["token_id"] == "42"

    provider.get_block_logs.assert_awaited_once_with(
        block_number=100,
    )


@pytest.mark.asyncio
async def test_pipeline_processes_nft_mint():
    pipeline, engine, _ = make_pipeline(
        logs=[
            make_log(
                token_id=5,
                from_address=ZERO_ADDRESS,
            )
        ]
    )

    received = []

    async def handler(event):
        received.append(event)

    engine.subscribe(EventType.NFT_MINT, handler)

    count = await pipeline.process_block(100)

    assert count == 1
    assert len(received) == 1
    assert received[0].event_type == EventType.NFT_MINT


@pytest.mark.asyncio
async def test_pipeline_handles_multiple_logs():
    pipeline, engine, _ = make_pipeline(
        logs=[
            make_log(token_id=1),
            make_log(token_id=2),
            make_log(token_id=3),
        ]
    )

    received = []

    async def handler(event):
        received.append(event)

    engine.subscribe(EventType.NFT_TRANSFER, handler)

    count = await pipeline.process_block(100)

    assert count == 3
    assert len(received) == 3


@pytest.mark.asyncio
async def test_pipeline_handles_empty_block():
    pipeline, _, _ = make_pipeline(logs=[])

    count = await pipeline.process_block(100)

    assert count == 0


@pytest.mark.asyncio
async def test_pipeline_receives_block_event():
    pipeline, engine, provider = make_pipeline(
        logs=[make_log()]
    )

    pipeline.start()

    await engine.publish(make_block_event())

    provider.get_block_logs.assert_awaited_once_with(
        block_number=100,
    )

    pipeline.stop()


@pytest.mark.asyncio
async def test_pipeline_ignores_other_chain():
    pipeline, engine, provider = make_pipeline()

    pipeline.start()

    await engine.publish(
        make_block_event(chain_id=137)
    )

    provider.get_block_logs.assert_not_awaited()

    pipeline.stop()


@pytest.mark.asyncio
async def test_pipeline_ignores_invalid_payload():
    pipeline, engine, provider = make_pipeline()

    pipeline.start()

    event = BlockchainEvent(
        event_type=EventType.BLOCK_MINED,
        source="test",
        chain_id=1,
        payload={"block_number": "invalid"},
    )

    await engine.publish(event)

    provider.get_block_logs.assert_not_awaited()

    pipeline.stop()


@pytest.mark.asyncio
async def test_pipeline_prevents_concurrent_duplicate_processing():
    pipeline, _, provider = make_pipeline(
        logs=[make_log()]
    )

    started = asyncio.Event()
    release = asyncio.Event()

    async def delayed_get_logs(*args, **kwargs):
        started.set()
        await release.wait()
        return [make_log()]

    provider.get_block_logs.side_effect = delayed_get_logs

    first = asyncio.create_task(
        pipeline.process_block(100)
    )

    await started.wait()

    second = asyncio.create_task(
        pipeline.process_block(100)
    )

    await asyncio.sleep(0)
    release.set()

    results = await asyncio.gather(first, second)

    assert results == [1, 1]
    assert provider.get_block_logs.await_count == 1


@pytest.mark.asyncio
async def test_pipeline_propagates_rpc_error():
    pipeline, _, provider = make_pipeline()

    provider.get_block_logs.side_effect = ConnectionError(
        "RPC unavailable"
    )

    with pytest.raises(ConnectionError):
        await pipeline.process_block(100)


@pytest.mark.asyncio
async def test_pipeline_can_retry_after_failure():
    pipeline, _, provider = make_pipeline()

    provider.get_block_logs.side_effect = ConnectionError(
        "Temporary RPC failure"
    )

    with pytest.raises(ConnectionError):
        await pipeline.process_block(100)

    provider.get_block_logs.side_effect = None
    provider.get_block_logs.return_value = [make_log()]

    count = await pipeline.process_block(100)

    assert count == 1
    assert provider.get_block_logs.await_count == 2


@pytest.mark.asyncio
async def test_pipeline_rejects_negative_block():
    pipeline, _, _ = make_pipeline()

    with pytest.raises(ValueError):
        await pipeline.process_block(-1)


def test_pipeline_rejects_invalid_chain_id():
    with pytest.raises(ValueError):
        make_pipeline(chain_id=0)


def test_pipeline_start_stop_is_idempotent():
    pipeline, engine, _ = make_pipeline()

    pipeline.start()
    pipeline.start()

    assert engine.subscriber_count(EventType.BLOCK_MINED) == 1

    pipeline.stop()
    pipeline.stop()

    assert engine.subscriber_count(EventType.BLOCK_MINED) == 0
