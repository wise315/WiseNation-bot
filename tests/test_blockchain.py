
import pytest

from app.blockchain.service import BlockchainService
from app.core.config import get_settings


@pytest.mark.asyncio
async def test_ethereum_rpc_connection():
    settings = get_settings()
    blockchain = BlockchainService()

    try:
        connected = await blockchain.ethereum.is_connected()
        assert connected is True
    finally:
        await blockchain.ethereum.close()


@pytest.mark.asyncio
async def test_ethereum_chain_id():
    settings = get_settings()
    blockchain = BlockchainService()

    try:
        chain_id = await blockchain.ethereum.get_chain_id()
        assert chain_id == settings.ethereum_chain_id
    finally:
        await blockchain.ethereum.close()


@pytest.mark.asyncio
async def test_ethereum_block_number():
    blockchain = BlockchainService()

    try:
        block_number = await blockchain.ethereum.get_block_number()
        assert isinstance(block_number, int)
        assert block_number > 0
    finally:
        await blockchain.ethereum.close()


@pytest.mark.asyncio
async def test_ethereum_balance():
    blockchain = BlockchainService()

    try:
        address = "0x0000000000000000000000000000000000000000"
        balance = await blockchain.ethereum.get_balance(address)

        assert isinstance(balance, int)
        assert balance >= 0
    finally:
        await blockchain.ethereum.close()
