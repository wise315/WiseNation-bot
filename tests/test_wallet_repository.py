from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.database.models import Chain, User, Wallet
from app.database.session import AsyncSessionLocal
from app.repositories.wallets import WalletRepository


TEST_TELEGRAM_ID = 999999999998
TEST_CHAIN_ID = 1
TEST_WALLET_ADDRESS = "0x0000000000000000000000000000000000000001"


@pytest.mark.asyncio
async def test_wallet_repository_can_create_and_read_wallet():
    async with AsyncSessionLocal() as session:
        # Clean up previous test data.
        existing_user_result = await session.execute(
            select(User).where(
                User.telegram_id == TEST_TELEGRAM_ID
            )
        )

        existing_user = existing_user_result.scalar_one_or_none()

        if existing_user:
            existing_wallets_result = await session.execute(
                select(Wallet).where(
                    Wallet.user_id == existing_user.id
                )
            )

            for wallet in existing_wallets_result.scalars().all():
                await session.delete(wallet)

            await session.delete(existing_user)
            await session.commit()

        # Find Ethereum chain.
        chain_result = await session.execute(
            select(Chain).where(
                Chain.chain_id == TEST_CHAIN_ID
            )
        )

        chain = chain_result.scalar_one_or_none()

        # Create Ethereum only if the table is still empty.
        chain_created_by_test = False

        if chain is None:
            chain = Chain(
                name="Ethereum",
                chain_id=TEST_CHAIN_ID,
                rpc_url=None,
                is_active=True,
            )

            session.add(chain)
            await session.flush()

            chain_created_by_test = True

        # Create test user.
        user = User(
            telegram_id=TEST_TELEGRAM_ID,
            username="wallet_repo_test",
            first_name="WalletRepo",
            subscription_tier="free",
            is_banned=False,
            created_at=datetime.now(timezone.utc),
        )

        session.add(user)
        await session.flush()

        repository = WalletRepository(session)

        wallet = await repository.create(
            user_id=user.id,
            chain_id=chain.id,
            address=TEST_WALLET_ADDRESS,
            label="Repository Test Wallet",
            wallet_type="watch_only",
            encrypted_private_key=None,
            is_default=True,
        )

        await session.commit()

        assert wallet.id is not None
        assert wallet.user_id == user.id
        assert wallet.chain_id == chain.id
        assert wallet.address == TEST_WALLET_ADDRESS
        assert wallet.label == "Repository Test Wallet"
        assert wallet.wallet_type == "watch_only"
        assert wallet.encrypted_private_key is None
        assert wallet.is_default is True

        # Test get_by_id().
        found_wallet = await repository.get_by_id(wallet.id)

        assert found_wallet is not None
        assert found_wallet.id == wallet.id
        assert found_wallet.address == TEST_WALLET_ADDRESS

        # Test get_by_user_id().
        user_wallets = await repository.get_by_user_id(user.id)

        assert len(user_wallets) == 1
        assert user_wallets[0].id == wallet.id

        # Test get_default_by_user_id().
        default_wallet = await repository.get_default_by_user_id(
            user.id
        )

        assert default_wallet is not None
        assert default_wallet.id == wallet.id

        # Test delete().
        deleted = await repository.delete(wallet.id)

        assert deleted is True

        await session.commit()

        deleted_wallet = await repository.get_by_id(wallet.id)

        assert deleted_wallet is None

        # Clean up the test user.
        await session.delete(user)

        # Only remove the chain if this test created it.
        if chain_created_by_test:
            await session.delete(chain)

        await session.commit()