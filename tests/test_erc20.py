from decimal import Decimal

import pytest

from app.blockchain.service import BlockchainService


USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


@pytest.mark.asyncio
async def test_ethereum_usdc_symbol():
    blockchain = BlockchainService()

    reader = blockchain.ethereum.get_erc20_reader()

    symbol = await reader.get_symbol(USDC_ADDRESS)

    assert symbol == "USDC"


@pytest.mark.asyncio
async def test_ethereum_usdc_zero_address_balance():
    blockchain = BlockchainService()

    reader = blockchain.ethereum.get_erc20_reader()

    balance = await reader.get_balance(
        token_address=USDC_ADDRESS,
        wallet_address=ZERO_ADDRESS,
    )

    assert isinstance(balance, Decimal)
    assert balance == Decimal("0")