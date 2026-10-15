from datetime import datetime, timezone
from decimal import Decimal

from app.schemas.transaction import WalletTransaction


def test_wallet_transaction_schema():
    transaction = WalletTransaction(
        hash="0x1234567890abcdef",
        wallet_address="0x1111111111111111111111111111111111111111",
        from_address="0x2222222222222222222222222222222222222222",
        to_address="0x3333333333333333333333333333333333333333",
        value=Decimal("0.25"),
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

    assert transaction.hash == "0x1234567890abcdef"
    assert transaction.wallet_address == (
        "0x1111111111111111111111111111111111111111"
    )
    assert transaction.from_address == (
        "0x2222222222222222222222222222222222222222"
    )
    assert transaction.to_address == (
        "0x3333333333333333333333333333333333333333"
    )
    assert transaction.value == Decimal("0.25")
    assert transaction.block_number == 12345678
    assert transaction.status == "success"


def test_wallet_transaction_allows_missing_recipient_and_timestamp():
    transaction = WalletTransaction(
        hash="0xabcdef",
        wallet_address="0x1111111111111111111111111111111111111111",
        from_address="0x2222222222222222222222222222222222222222",
        value=Decimal("0"),
        block_number=12345679,
        status="pending",
    )

    assert transaction.to_address is None
    assert transaction.timestamp is None
    assert transaction.status == "pending"