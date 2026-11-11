
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.events.schemas import BlockchainEvent, EventType
from app.services.nft_blockchain_event_service import (
    NFTBlockchainEventService,
)


BLOCK_HASH = "0x" + "a" * 64
TX_HASH = "0x" + "b" * 64


@pytest.fixture
def session():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def service(session):
    return NFTBlockchainEventService(session)


def make_event(
    event_type=EventType.NFT_TRANSFER,
    batch_index=None,
):
    payload = {
        "contract_address": "0x" + "c" * 40,
        "transaction_hash": TX_HASH,
        "block_number": 103,
        "log_index": 5,
        "token_standard": "ERC721",
        "from_address": "0x" + "d" * 40,
        "to_address": "0x" + "e" * 40,
        "token_id": "42",
        "amount": 1,
    }

    if batch_index is not None:
        payload["batch_index"] = batch_index
        payload["token_standard"] = "ERC1155"

    return BlockchainEvent(
        event_type=event_type,
        source="ethereum_contract_log",
        chain_id=1,
        payload=payload,
    )


@pytest.mark.asyncio
async def test_save_new_event(service, session):
    result = MagicMock()
    result.scalar_one_or_none.return_value = 1
    session.execute.return_value = result

    inserted = await service.save_event(
        make_event(),
        BLOCK_HASH,
    )

    assert inserted is True
    session.execute.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_duplicate_event_returns_false(service, session):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    inserted = await service.save_event(
        make_event(),
        BLOCK_HASH,
    )

    assert inserted is False
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_save_mint_event(service, session):
    result = MagicMock()
    result.scalar_one_or_none.return_value = 2
    session.execute.return_value = result

    inserted = await service.save_event(
        make_event(EventType.NFT_MINT),
        BLOCK_HASH,
    )

    assert inserted is True


@pytest.mark.asyncio
async def test_save_erc1155_batch_event(service, session):
    result = MagicMock()
    result.scalar_one_or_none.return_value = 3
    session.execute.return_value = result

    inserted = await service.save_event(
        make_event(batch_index=2),
        BLOCK_HASH,
    )

    assert inserted is True


@pytest.mark.asyncio
async def test_save_multiple_events(service, session):
    results = [MagicMock(), MagicMock(), MagicMock()]

    results[0].scalar_one_or_none.return_value = 1
    results[1].scalar_one_or_none.return_value = None
    results[2].scalar_one_or_none.return_value = 3

    session.execute.side_effect = results

    count = await service.save_events(
        [
            make_event(),
            make_event(),
            make_event(batch_index=1),
        ],
        BLOCK_HASH,
    )

    assert count == 2
    assert session.execute.await_count == 3
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_unsupported_event_rejected(service, session):
    event = make_event(EventType.BLOCK_MINED)

    with pytest.raises(ValueError):
        await service.save_event(event, BLOCK_HASH)

    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_transaction_hash(service, session):
    event = make_event()
    del event.payload["transaction_hash"]

    with pytest.raises(ValueError):
        await service.save_event(event, BLOCK_HASH)

    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_block_hash(service, session):
    with pytest.raises(ValueError):
        await service.save_event(
            make_event(),
            "invalid",
        )

    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_log_index(service, session):
    event = make_event()
    event.payload["log_index"] = -1

    with pytest.raises(ValueError):
        await service.save_event(event, BLOCK_HASH)

    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_batch_index(service, session):
    event = make_event(batch_index=-1)

    with pytest.raises(ValueError):
        await service.save_event(event, BLOCK_HASH)

    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_block_events(service, session):
    expected = [MagicMock(), MagicMock()]

    result = MagicMock()
    result.scalars.return_value.all.return_value = expected
    session.execute.return_value = result

    events = await service.get_block_events(1, 103)

    assert events == expected
    session.execute.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_transaction_events(service, session):
    expected = [MagicMock()]

    result = MagicMock()
    result.scalars.return_value.all.return_value = expected
    session.execute.return_value = result

    events = await service.get_transaction_events(
        1,
        TX_HASH,
    )

    assert events == expected


@pytest.mark.asyncio
async def test_mark_blocks_orphaned(service, session):
    result = MagicMock()
    result.rowcount = 2
    session.execute.return_value = result

    count = await service.mark_blocks_orphaned(
        chain_id=1,
        ancestor_block=101,
    )

    assert count == 2
    session.execute.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_orphan_marking_is_idempotent(service, session):
    first = MagicMock()
    first.rowcount = 2

    second = MagicMock()
    second.rowcount = 0

    session.execute.side_effect = [first, second]

    first_count = await service.mark_blocks_orphaned(
        1, 101
    )
    second_count = await service.mark_blocks_orphaned(
        1, 101
    )

    assert first_count == 2
    assert second_count == 0
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_ancestor_rejected(service, session):
    with pytest.raises(ValueError):
        await service.mark_blocks_orphaned(
            chain_id=1,
            ancestor_block=-1,
        )

    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_transaction_hash(service, session):
    with pytest.raises(ValueError):
        await service.get_transaction_events(
            1,
            "invalid",
        )

    session.execute.assert_not_awaited()
