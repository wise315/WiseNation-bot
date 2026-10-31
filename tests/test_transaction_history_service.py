
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.database.models.chain import Chain
from app.database.session import AsyncSessionLocal
from app.schemas.transaction import WalletTransaction
from app.services.user_service import UserService
from app.services.wallet_service import WalletService


class FakeTransactionProvider:
    async def get_transactions(
        self,
        address: str,
        limit: int = 10,
    ) -> list[WalletTransaction]:
        return [
            WalletTransaction(
                hash="0x1234567890abcdef",
                wallet_address=address,
                from_address=(
                    "0x0000000000000000000000000000000000000001"
                ),
                to_address=(
                    "0x0000000000000000000000000000000000000002"
                ),
                value=Decimal("0.5"),
                block_number=12345678,
                timestamp=datetime(
                    2026,
                    1,
                    1,
                    tzinfo=timezone.utc,
                ),
                status="success",
            )
        ]


async def get_ethereum_chain_id(session) -> int:
    """
    Retrieve Ethereum's internal PostgreSQL primary key.

    Ethereum network ID = 1.
    The database record ID may be different.
    """
    result = await session.execute(
        select(Chain).where(Chain.chain_id == 1)
    )

    ethereum = result.scalar_one_or_none()

    if ethereum is None:
        raise AssertionError(
            "Ethereum is missing from the chains table. "
            "Create the Ethereum chain record before running "
            "these tests."
        )

    return ethereum.id


@pytest.mark.asyncio
async def test_get_transaction_history_returns_transactions():
    async with AsyncSessionLocal() as session:
        ethereum_chain_id = await get_ethereum_chain_id(session)

        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=990000001,
            username="transaction_test_user",
            first_name="Transaction",
        )

        wallet_service = WalletService(
            session,
            transaction_provider=FakeTransactionProvider(),
        )

        wallet = await wallet_service.add_wallet(
            user_id=user.id,
            chain_id=ethereum_chain_id,
            address=(
                "0x0000000000000000000000000000000000000001"
            ),
            label="Transaction Test Wallet",
        )

        transactions = await wallet_service.get_transaction_history(
            user_id=user.id,
            wallet_id=wallet.id,
            limit=10,
        )

        assert len(transactions) == 1

        transaction = transactions[0]

        assert transaction.hash == "0x1234567890abcdef"
        assert (
            transaction.wallet_address
            == "0x0000000000000000000000000000000000000001"
        )
        assert transaction.value == Decimal("0.5")
        assert transaction.block_number == 12345678
        assert transaction.status == "success"


@pytest.mark.asyncio
async def test_get_transaction_history_rejects_other_users_wallet():
    async with AsyncSessionLocal() as session:
        ethereum_chain_id = await get_ethereum_chain_id(session)

        user_service = UserService(session)

        owner, _ = await user_service.get_or_create_user(
            telegram_id=990000002,
            username="transaction_owner",
            first_name="Owner",
        )

        other_user, _ = await user_service.get_or_create_user(
            telegram_id=990000003,
            username="transaction_other",
            first_name="Other",
        )

        wallet_service = WalletService(
            session,
            transaction_provider=FakeTransactionProvider(),
        )

        wallet = await wallet_service.add_wallet(
            user_id=owner.id,
            chain_id=ethereum_chain_id,
            address=(
                "0x0000000000000000000000000000000000000002"
            ),
            label="Owner Wallet",
        )

        transactions = await wallet_service.get_transaction_history(
            user_id=other_user.id,
            wallet_id=wallet.id,
            limit=10,
        )

        assert transactions is None
