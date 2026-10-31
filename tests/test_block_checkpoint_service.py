
import pytest

from app.database.session import AsyncSessionLocal
from app.services.block_checkpoint_service import BlockCheckpointService


@pytest.mark.asyncio
async def test_checkpoint_initially_missing():
    async with AsyncSessionLocal() as session:
        service = BlockCheckpointService(session)

        checkpoint = await service.get_checkpoint(
            chain_id=999999901,
        )

        assert checkpoint is None


@pytest.mark.asyncio
async def test_save_and_read_checkpoint():
    async with AsyncSessionLocal() as session:
        service = BlockCheckpointService(session)

        checkpoint = await service.save_checkpoint(
            chain_id=999999902,
            block_number=100,
            block_hash="0x" + "a" * 64,
        )

        assert checkpoint.chain_id == 999999902
        assert checkpoint.last_processed_block == 100
        assert checkpoint.block_hash == "0x" + "a" * 64

        loaded = await service.get_checkpoint(999999902)

        assert loaded is not None
        assert loaded.last_processed_block == 100

        await session.rollback()


@pytest.mark.asyncio
async def test_checkpoint_advances_forward():
    async with AsyncSessionLocal() as session:
        service = BlockCheckpointService(session)

        await service.save_checkpoint(
            chain_id=999999903,
            block_number=100,
        )

        checkpoint = await service.save_checkpoint(
            chain_id=999999903,
            block_number=105,
        )

        assert checkpoint.last_processed_block == 105

        await session.rollback()


@pytest.mark.asyncio
async def test_checkpoint_does_not_move_backward():
    async with AsyncSessionLocal() as session:
        service = BlockCheckpointService(session)

        await service.save_checkpoint(
            chain_id=999999904,
            block_number=105,
        )

        checkpoint = await service.save_checkpoint(
            chain_id=999999904,
            block_number=100,
        )

        assert checkpoint.last_processed_block == 105

        await session.rollback()


@pytest.mark.asyncio
async def test_checkpoint_does_not_replace_same_block_hash():
    async with AsyncSessionLocal() as session:
        service = BlockCheckpointService(session)

        await service.save_checkpoint(
            chain_id=999999905,
            block_number=100,
            block_hash="0x" + "a" * 64,
        )

        checkpoint = await service.save_checkpoint(
            chain_id=999999905,
            block_number=100,
            block_hash="0x" + "b" * 64,
        )

        assert checkpoint.last_processed_block == 100
        assert checkpoint.block_hash == "0x" + "a" * 64

        await session.rollback()


@pytest.mark.asyncio
async def test_checkpoint_rejects_invalid_block_number():
    async with AsyncSessionLocal() as session:
        service = BlockCheckpointService(session)

        with pytest.raises(ValueError):
            await service.save_checkpoint(
                chain_id=1,
                block_number=-1,
            )

        with pytest.raises(ValueError):
            await service.save_checkpoint(
                chain_id=1,
                block_number=True,
            )


@pytest.mark.asyncio
async def test_checkpoint_rejects_invalid_hash():
    async with AsyncSessionLocal() as session:
        service = BlockCheckpointService(session)

        with pytest.raises(ValueError):
            await service.save_checkpoint(
                chain_id=1,
                block_number=100,
                block_hash="invalid",
            )


@pytest.mark.asyncio
async def test_checkpoint_rejects_invalid_chain_id():
    async with AsyncSessionLocal() as session:
        service = BlockCheckpointService(session)

        with pytest.raises(ValueError):
            await service.get_checkpoint(0)

        with pytest.raises(ValueError):
            await service.save_checkpoint(
                chain_id=-1,
                block_number=100,
            )
