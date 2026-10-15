from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest

from app.blockchain.providers.etherscan import (
    EtherscanTransactionProvider,
)


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "status": "1",
            "message": "OK",
            "result": [
                {
                    "hash": "0x123",
                    "from": "0x1111111111111111111111111111111111111111",
                    "to": "0x2222222222222222222222222222222222222222",
                    "value": "250000000000000000",
                    "blockNumber": "12345678",
                    "timeStamp": "1779366600",
                    "isError": "0",
                }
            ],
        }


class FakeClient:
    def __init__(self):
        self.request_params = None

    async def get(self, url, params=None):
        self.request_params = params
        return FakeResponse()


@pytest.mark.asyncio
async def test_etherscan_transaction_provider():
    client = FakeClient()

    provider = EtherscanTransactionProvider(
        api_key="test-key",
        chain_id=1,
        client=client,
    )

    transactions = await provider.get_transactions(
        address="0x3333333333333333333333333333333333333333",
        limit=10,
    )

    assert len(transactions) == 1

    transaction = transactions[0]

    assert transaction.hash == "0x123"
    assert transaction.wallet_address == (
        "0x3333333333333333333333333333333333333333"
    )
    assert transaction.value == Decimal("0.25")
    assert transaction.block_number == 12345678
    assert transaction.status == "success"
    assert transaction.timestamp == datetime.fromtimestamp(
        1779366600,
        tz=timezone.utc,
    )

    assert client.request_params["chainid"] == 1
    assert client.request_params["module"] == "account"
    assert client.request_params["action"] == "txlist"
    assert client.request_params["page"] == 1
    assert client.request_params["offset"] == 10
    assert client.request_params["sort"] == "desc"
    assert client.request_params["apikey"] == "test-key"


@pytest.mark.asyncio
async def test_etherscan_transaction_provider_returns_empty_on_api_error():
    class ErrorResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "status": "0",
                "message": "No transactions found",
                "result": [],
            }

    class ErrorClient:
        async def get(self, url, params=None):
            return ErrorResponse()

    provider = EtherscanTransactionProvider(
        api_key="test-key",
        client=ErrorClient(),
    )

    transactions = await provider.get_transactions(
        address="0x3333333333333333333333333333333333333333",
    )

    assert transactions == []