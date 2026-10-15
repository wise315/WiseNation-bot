import pytest
from sqlalchemy import select

from app.database.models import Wallet
from app.database.session import AsyncSessionLocal


@pytest.mark.asyncio
async def test_wallet_table_can_be_read():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Wallet).limit(1)
        )

        wallet = result.scalar_one_or_none()

        # The wallets table may currently be empty.
        # The important thing is that SQLAlchemy can query it successfully.
        assert wallet is None or isinstance(wallet, Wallet)