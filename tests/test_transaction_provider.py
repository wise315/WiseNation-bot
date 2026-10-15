from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.blockchain.providers.transaction import (
    TransactionHistoryProvider,
)
from app.schemas.transaction import WalletTransaction


class FakeTransactionProvider(TransactionHistoryProvider):
    async def get_transactions(
        self,
        address: str,
        limit: int = 10,
    ) -> list[WalletTransaction]:
        return [
            WalletTransaction(
                hash="0x123",
                wallet_address=address,
                from_address="0x1111111111111111111111111111111111111111",
                to_address="0x2222222222222222222222222222222222222222",
                value=Decimal("0.5"),
                block_number=12345678,
                timestamp=datetime(
                    2026,
                    9,
                    21,
                    12,
                    30,
                    tzinfo=timezone.utc,
                ),
                status="success",
            )
        ]


@pytest.mark.asyncio
async def test_transaction_history_provider_returns_transactions():
    provider = FakeTransactionProvider()

    transactions = await provider.get_transactions(
        address="0x3333333333333333333333333333333333333333",
        limit=10,
    )

    assert len(transactions) == 1
    assert transactions[0].hash == "0x123"
    assert transactions[0].value == Decimal("0.5")
    assert transactions[0].status == "success"


def test_transaction_history_provider_is_abstract():
    with pytest.raises(TypeError):
        TransactionHistoryProvider()