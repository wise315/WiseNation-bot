
import os
from contextlib import asynccontextmanager

import pytest
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)

from app.events.schemas import BlockchainEvent, EventType
from app.services.nft_blockchain_event_service import (
    NFTBlockchainEventService,
)


load_dotenv()

BLOCK_HASH = "0x" + "a" * 64
OTHER_BLOCK_HASH = "0x" + "b" * 64
TX_HASH = "0x" + "c" * 64



@asynccontextmanager
async def integration_session():
    """Open a real PostgreSQL session with rollback isolation."""

    database_url = os.getenv("TEST_DATABASE_URL")

    if not database_url:
        pytest.fail("TEST_DATABASE_URL is not configured.")

    parsed_url = make_url(database_url)

    if parsed_url.database != "nft_bot_test":
        pytest.fail(
            "Integration tests must use nft_bot_test."
        )

    engine = create_async_engine(database_url)

    try:
        async with engine.connect() as connection:

            # Start the outer transaction BEFORE executing SQL.
            transaction = await connection.begin()

            try:
                result = await connection.execute(
                    text("SELECT current_database()")
                )

                actual_database = result.scalar_one()

                if actual_database != "nft_bot_test":
                    pytest.fail(
                        f"Unsafe database: {actual_database}"
                    )

                async with AsyncSession(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                ) as session:
                    yield session

            finally:
                if transaction.is_active:
                    await transaction.rollback()

    finally:
        await engine.dispose()


BLOCK_HASH = "0x" + "a" * 64
OTHER_BLOCK_HASH = "0x" + "b" * 64
TX_HASH = "0x" + "c" * 64


def make_event(
    *,
    chain_id=1,
    block_number=100,
    transaction_hash=TX_HASH,
    log_index=0,
    batch_index=0,
    event_type=EventType.NFT_TRANSFER,
):
    """Create a valid NFT blockchain event for integration tests."""

    return BlockchainEvent(
        event_type=event_type,
        source="ethereum",
        chain_id=chain_id,
        payload={
            "block_number": block_number,
            "transaction_hash": transaction_hash,
            "log_index": log_index,
            "batch_index": batch_index,
            "contract_address": "0x" + "d" * 40,
            "from_address": "0x" + "e" * 40,
            "to_address": "0x" + "f" * 40,
            "token_id": "123",
            "amount": 1,
            "token_standard": "ERC721",
        },
    )



@pytest.mark.asyncio
async def test_insert_and_retrieve_nft_event():
    async with integration_session() as session:
        service = NFTBlockchainEventService(session)

        event = make_event()

        inserted = await service.save_event(
            event,
            BLOCK_HASH,
        )

        assert inserted is True

        events = await service.get_block_events(
            chain_id=1,
            block_number=100,
        )

        assert len(events) == 1
        assert events[0].event_type == "nft.transfer"
        assert events[0].block_hash == BLOCK_HASH
        assert events[0].is_canonical is True


@pytest.mark.asyncio
async def test_duplicate_event_is_not_inserted():
    async with integration_session() as session:
        service = NFTBlockchainEventService(session)

        event = make_event()

        first = await service.save_event(
            event,
            BLOCK_HASH,
        )

        second = await service.save_event(
            event,
            BLOCK_HASH,
        )

        assert first is True
        assert second is False

        events = await service.get_block_events(
            chain_id=1,
            block_number=100,
        )

        assert len(events) == 1


@pytest.mark.asyncio
async def test_erc1155_batch_events():
    async with integration_session() as session:
        service = NFTBlockchainEventService(session)

        first = make_event(batch_index=0)
        second = make_event(batch_index=1)
        third = make_event(batch_index=2)

        for event in (first, second, third):
            event.payload["token_standard"] = "ERC1155"

        inserted = await service.save_events(
            [first, second, third],
            BLOCK_HASH,
        )

        assert inserted == 3

        events = await service.get_transaction_events(
            chain_id=1,
            transaction_hash=TX_HASH,
        )

        assert len(events) == 3
        assert [
            event.batch_index for event in events
        ] == [0, 1, 2]


@pytest.mark.asyncio
async def test_database_transaction_rollback():
    async with integration_session() as session:
        service = NFTBlockchainEventService(session)

        await service.save_event(
            make_event(),
            BLOCK_HASH,
        )

        await session.rollback()

        events = await service.get_block_events(
            chain_id=1,
            block_number=100,
        )

        assert events == []


@pytest.mark.asyncio
async def test_orphaned_events_are_excluded():
    async with integration_session() as session:
        service = NFTBlockchainEventService(session)

        await service.save_event(
            make_event(block_number=100),
            BLOCK_HASH,
        )

        await service.save_event(
            make_event(block_number=101),
            OTHER_BLOCK_HASH,
        )

        updated = await service.mark_blocks_orphaned(
            chain_id=1,
            ancestor_block=100,
        )

        assert updated == 1

        canonical_events = await service.get_block_events(
            chain_id=1,
            block_number=101,
        )

        all_events = await service.get_block_events(
            chain_id=1,
            block_number=101,
            canonical_only=False,
        )

        assert canonical_events == []
        assert len(all_events) == 1
        assert all_events[0].is_canonical is False

        ancestor_events = await service.get_block_events(
            chain_id=1,
            block_number=100,
        )

        assert len(ancestor_events) == 1
        assert ancestor_events[0].is_canonical is True


@pytest.mark.asyncio
async def test_events_are_isolated_by_chain():
    async with integration_session() as session:
        service = NFTBlockchainEventService(session)

        await service.save_event(
            make_event(chain_id=1),
            BLOCK_HASH,
        )

        await service.save_event(
            make_event(chain_id=137),
            BLOCK_HASH,
        )

        updated = await service.mark_blocks_orphaned(
            chain_id=1,
            ancestor_block=99,
        )

        assert updated == 1

        ethereum_events = await service.get_block_events(
            chain_id=1,
            block_number=100,
        )

        polygon_events = await service.get_block_events(
            chain_id=137,
            block_number=100,
        )

        assert ethereum_events == []
        assert len(polygon_events) == 1
        assert polygon_events[0].is_canonical is True
