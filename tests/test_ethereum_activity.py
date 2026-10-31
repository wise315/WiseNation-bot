
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.blockchain.providers.ethereum_activity import (
    EthereumActivityProvider,
)
from app.schemas.blockchain_activity import (
    EthereumContractLog,
    EthereumTransaction,
)


def make_provider():
    web3 = MagicMock()
    web3.eth.get_block = AsyncMock()
    web3.eth.get_logs = AsyncMock()

    return EthereumActivityProvider(web3), web3


@pytest.mark.asyncio
async def test_get_block_transactions():
    provider, web3 = make_provider()

    web3.eth.get_block.return_value = {
        "transactions": [
            {
                "hash": bytes.fromhex("ab" * 32),
                "blockNumber": 100,
                "transactionIndex": 0,
                "from": "0xSender",
                "to": "0xReceiver",
                "value": 10**18,
                "input": b"",
            }
        ]
    }

    transactions = await provider.get_block_transactions(100)

    assert len(transactions) == 1
    assert transactions[0].transaction_hash == "0x" + "ab" * 32
    assert transactions[0].value_wei == 10**18
    assert transactions[0].block_number == 100

    web3.eth.get_block.assert_awaited_once_with(
        100,
        full_transactions=True,
    )


@pytest.mark.asyncio
async def test_empty_block_transactions():
    provider, web3 = make_provider()

    web3.eth.get_block.return_value = {
        "transactions": []
    }

    transactions = await provider.get_block_transactions(100)

    assert transactions == []


@pytest.mark.asyncio
async def test_contract_creation_transaction():
    provider, web3 = make_provider()

    web3.eth.get_block.return_value = {
        "transactions": [
            {
                "hash": "0xabc",
                "blockNumber": 100,
                "transactionIndex": 0,
                "from": "0xSender",
                "to": None,
                "value": 0,
                "input": "0x1234",
            }
        ]
    }

    transactions = await provider.get_block_transactions(100)

    assert transactions[0].to_address is None
    assert transactions[0].input_data == "0x1234"


@pytest.mark.asyncio
async def test_get_block_logs():
    provider, web3 = make_provider()

    web3.eth.get_logs.return_value = [
        {
            "transactionHash": bytes.fromhex("cd" * 32),
            "blockNumber": 100,
            "logIndex": 2,
            "address": "0xContract",
            "topics": [
                bytes.fromhex("aa" * 32),
            ],
            "data": b"",
            "removed": False,
        }
    ]

    logs = await provider.get_block_logs(100)

    assert len(logs) == 1
    assert logs[0].log_index == 2
    assert logs[0].contract_address == "0xContract"
    assert logs[0].topics == ["0x" + "aa" * 32]

    web3.eth.get_logs.assert_awaited_once_with(
        {
            "fromBlock": 100,
            "toBlock": 100,
        }
    )


@pytest.mark.asyncio
async def test_get_block_logs_with_filters():
    provider, web3 = make_provider()

    web3.eth.get_logs.return_value = []

    await provider.get_block_logs(
        block_number=100,
        contract_addresses=["0xContract"],
        topics=["0xTopic"],
    )

    web3.eth.get_logs.assert_awaited_once_with(
        {
            "fromBlock": 100,
            "toBlock": 100,
            "address": ["0xContract"],
            "topics": ["0xTopic"],
        }
    )


@pytest.mark.asyncio
async def test_empty_logs():
    provider, web3 = make_provider()

    web3.eth.get_logs.return_value = []

    logs = await provider.get_block_logs(100)

    assert logs == []


@pytest.mark.asyncio
async def test_invalid_block_number():
    provider, web3 = make_provider()

    with pytest.raises(ValueError):
        await provider.get_block_transactions(-1)

    with pytest.raises(ValueError):
        await provider.get_block_logs(-1)

    web3.eth.get_block.assert_not_awaited()
    web3.eth.get_logs.assert_not_awaited()


@pytest.mark.asyncio
async def test_rpc_error_propagates():
    provider, web3 = make_provider()

    web3.eth.get_block.side_effect = ConnectionError(
        "RPC unavailable"
    )

    with pytest.raises(ConnectionError):
        await provider.get_block_transactions(100)


def test_transaction_schema_rejects_negative_value():
    with pytest.raises(ValidationError):
        EthereumTransaction(
            transaction_hash="0xabc",
            block_number=100,
            transaction_index=0,
            from_address="0xSender",
            value_wei=-1,
        )


def test_log_schema_rejects_negative_index():
    with pytest.raises(ValidationError):
        EthereumContractLog(
            transaction_hash="0xabc",
            block_number=100,
            log_index=-1,
            contract_address="0xContract",
        )
