import pytest
from sqlalchemy import select

from app.database.models import Chain
from app.database.session import AsyncSessionLocal


ETHEREUM_CHAIN_ID = 1


@pytest.mark.asyncio
async def test_chain_table_can_be_read():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Chain).where(
                Chain.chain_id == ETHEREUM_CHAIN_ID
            )
        )

        chain = result.scalar_one_or_none()

        # The table currently may be empty.
        # The important thing is that SQLAlchemy can query it successfully.
        assert chain is None or chain.chain_id == ETHEREUM_CHAIN_ID