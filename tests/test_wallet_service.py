from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select

from app.schemas.transaction import WalletTransaction
from app.database.models import Chain, User, Wallet
from app.database.session import AsyncSessionLocal
from app.services.wallet_service import WalletService

from decimal import Decimal

class FakeEthereum:
    async def get_balance(self, address: str) -> int:
        return 1_500_000_000_000_000_000


class FakeBlockchain:
    def __init__(self):
        self.ethereum = FakeEthereum()


TEST_TELEGRAM_ID = 999999999997
TEST_CHAIN_ID = 1

WALLET_ADDRESS_1 = "0x0000000000000000000000000000000000000011"
WALLET_ADDRESS_2 = "0x0000000000000000000000000000000000000022"


async def create_test_user_and_chain(session):
    user_result = await session.execute(
        select(User).where(
            User.telegram_id == TEST_TELEGRAM_ID
        )
    )

    user = user_result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=TEST_TELEGRAM_ID,
            username="wallet_service_test",
            first_name="WalletService",
            subscription_tier="free",
            is_banned=False,
            created_at=datetime.now(timezone.utc),
        )

        session.add(user)
        await session.flush()

    chain_result = await session.execute(
        select(Chain).where(
            Chain.chain_id == TEST_CHAIN_ID
        )
    )

    chain = chain_result.scalar_one_or_none()

    if chain is None:
        chain = Chain(
            name="Ethereum",
            chain_id=TEST_CHAIN_ID,
            rpc_url=None,
            is_active=True,
        )

        session.add(chain)
        await session.flush()

    return user, chain


async def cleanup_test_data(session):
    user_result = await session.execute(
        select(User).where(
            User.telegram_id == TEST_TELEGRAM_ID
        )
    )

    user = user_result.scalar_one_or_none()

    if user is None:
        return

    await session.execute(
        delete(Wallet).where(
            Wallet.user_id == user.id
        )
    )

    await session.flush()

    await session.execute(
        delete(User).where(
            User.id == user.id
        )
    )

    await session.commit()
    
@pytest.mark.asyncio
async def test_first_wallet_becomes_default():
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user, chain = await create_test_user_and_chain(
            session
        )

        service = WalletService(session)

        wallet = await service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=f"  {WALLET_ADDRESS_1}  ",
            label=" First Wallet ",
        )

        assert wallet.address == WALLET_ADDRESS_1
        assert wallet.label == "First Wallet"
        assert wallet.is_default is True
        assert wallet.wallet_type == "watch_only"

        await cleanup_test_data(session)


@pytest.mark.asyncio
async def test_second_wallet_is_not_default():
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user, chain = await create_test_user_and_chain(
            session
        )

        service = WalletService(session)

        first_wallet = await service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=WALLET_ADDRESS_1,
            label="First Wallet",
        )

        second_wallet = await service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=WALLET_ADDRESS_2,
            label="Second Wallet",
        )

        assert first_wallet.is_default is True
        assert second_wallet.is_default is False

        await cleanup_test_data(session)


@pytest.mark.asyncio
async def test_set_default_wallet():
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user, chain = await create_test_user_and_chain(
            session
        )

        service = WalletService(session)

        first_wallet = await service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=WALLET_ADDRESS_1,
            label="First Wallet",
        )

        second_wallet = await service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=WALLET_ADDRESS_2,
            label="Second Wallet",
        )

        updated_wallet = await service.set_default_wallet(
            user_id=user.id,
            wallet_id=second_wallet.id,
        )

        assert updated_wallet is not None
        assert updated_wallet.id == second_wallet.id
        assert updated_wallet.is_default is True

        refreshed_first = await service.get_wallet(
            user_id=user.id,
            wallet_id=first_wallet.id,
        )

        refreshed_second = await service.get_wallet(
            user_id=user.id,
            wallet_id=second_wallet.id,
        )

        assert refreshed_first is not None
        assert refreshed_second is not None

        assert refreshed_first.is_default is False
        assert refreshed_second.is_default is True

        await cleanup_test_data(session)


@pytest.mark.asyncio
async def test_user_cannot_access_another_users_wallet():
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user, chain = await create_test_user_and_chain(
            session
        )

        service = WalletService(session)

        wallet = await service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=WALLET_ADDRESS_1,
            label="Private Test Wallet",
        )

        another_user_id = user.id + 999999

        result = await service.get_wallet(
            user_id=another_user_id,
            wallet_id=wallet.id,
        )

        assert result is None

        await cleanup_test_data(session)


@pytest.mark.asyncio
async def test_remove_default_wallet_promotes_remaining_wallet():
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user, chain = await create_test_user_and_chain(
            session
        )

        service = WalletService(session)

        first_wallet = await service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=WALLET_ADDRESS_1,
            label="First Wallet",
        )

        second_wallet = await service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=WALLET_ADDRESS_2,
            label="Second Wallet",
        )

        assert first_wallet.is_default is True
        assert second_wallet.is_default is False

        removed = await service.remove_wallet(
            user_id=user.id,
            wallet_id=first_wallet.id,
        )

        assert removed is True

        remaining_wallet = await service.get_wallet(
            user_id=user.id,
            wallet_id=second_wallet.id,
        )

        assert remaining_wallet is not None
        assert remaining_wallet.is_default is True

        await cleanup_test_data(session)
        
@pytest.mark.asyncio
async def test_set_default_wallet_changes_default() -> None:
    async with AsyncSessionLocal() as session:
        user, chain = await create_test_user_and_chain(session)

        await cleanup_test_data(session)

        user, chain = await create_test_user_and_chain(session)

        wallet_service = WalletService(session)

        wallet_one = await wallet_service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=WALLET_ADDRESS_1,
            label="Wallet One",
        )

        wallet_two = await wallet_service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=WALLET_ADDRESS_2,
            label="Wallet Two",
        )

        assert wallet_one.is_default is True
        assert wallet_two.is_default is False

        updated_wallet = await wallet_service.set_default_wallet(
            user_id=user.id,
            wallet_id=wallet_two.id,
        )

        assert updated_wallet is not None
        assert updated_wallet.id == wallet_two.id
        assert updated_wallet.is_default is True

        wallets = await wallet_service.get_user_wallets(user.id)

        wallet_one_db = next(
            wallet for wallet in wallets
            if wallet.id == wallet_one.id
        )

        wallet_two_db = next(
            wallet for wallet in wallets
            if wallet.id == wallet_two.id
        )

        assert wallet_one_db.is_default is False
        assert wallet_two_db.is_default is True

        await cleanup_test_data(session)
        

@pytest.mark.asyncio
async def test_remove_wallet_removes_wallet() -> None:
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user, chain = await create_test_user_and_chain(session)

        wallet_service = WalletService(session)

        wallet = await wallet_service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=WALLET_ADDRESS_1,
            label="Wallet To Remove",
        )

        assert wallet.is_default is True

        removed = await wallet_service.remove_wallet(
            user_id=user.id,
            wallet_id=wallet.id,
        )

        assert removed is True

        found_wallet = await wallet_service.get_wallet(
            user_id=user.id,
            wallet_id=wallet.id,
        )

        assert found_wallet is None

        await cleanup_test_data(session)
        
@pytest.mark.asyncio
async def test_removing_default_wallet_promotes_remaining_wallet() -> None:
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user, chain = await create_test_user_and_chain(session)

        wallet_service = WalletService(session)

        wallet_one = await wallet_service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=WALLET_ADDRESS_1,
            label="Default Wallet",
        )

        wallet_two = await wallet_service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=WALLET_ADDRESS_2,
            label="Second Wallet",
        )

        assert wallet_one.is_default is True
        assert wallet_two.is_default is False

        removed = await wallet_service.remove_wallet(
            user_id=user.id,
            wallet_id=wallet_one.id,
        )

        assert removed is True

        remaining_wallets = (
            await wallet_service.get_user_wallets(user.id)
        )

        assert len(remaining_wallets) == 1
        assert remaining_wallets[0].id == wallet_two.id
        assert remaining_wallets[0].is_default is True

        await cleanup_test_data(session)
        
@pytest.mark.asyncio
async def test_user_cannot_remove_another_users_wallet() -> None:
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user, chain = await create_test_user_and_chain(session)

        wallet_service = WalletService(session)

        wallet = await wallet_service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=WALLET_ADDRESS_1,
            label="Protected Wallet",
        )

        different_user = User(
            telegram_id=999999999996,
            username="different_user",
            first_name="Different",
            subscription_tier="free",
            is_banned=False,
            created_at=datetime.now(timezone.utc),
        )

        session.add(different_user)
        await session.flush()

        removed = await wallet_service.remove_wallet(
            user_id=different_user.id,
            wallet_id=wallet.id,
        )

        assert removed is False

        wallet_still_exists = await wallet_service.get_wallet(
            user_id=user.id,
            wallet_id=wallet.id,
        )

        assert wallet_still_exists is not None

        await session.delete(different_user)
        await session.commit()

        await cleanup_test_data(session)
        
@pytest.mark.asyncio
async def test_get_native_balance() -> None:
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user, chain = await create_test_user_and_chain(session)

        wallet_service = WalletService(
            session,
            blockchain_service=FakeBlockchain(),
        )

        wallet = await wallet_service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=WALLET_ADDRESS_1,
            label="Balance Wallet",
        )

        balance = await wallet_service.get_native_balance(
            user_id=user.id,
            wallet_id=wallet.id,
        )

        assert balance == Decimal("1.5")

        await cleanup_test_data(session)
        
@pytest.mark.asyncio
async def test_user_cannot_get_balance_of_another_users_wallet() -> None:
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user, chain = await create_test_user_and_chain(session)

        wallet_service = WalletService(
            session,
            blockchain_service=FakeBlockchain(),
        )

        wallet = await wallet_service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=WALLET_ADDRESS_1,
            label="Protected Balance Wallet",
        )

        different_user = User(
            telegram_id=999999999996,
            username="different_user",
            first_name="Different",
            subscription_tier="free",
            is_banned=False,
            created_at=datetime.now(timezone.utc),
        )

        session.add(different_user)
        await session.flush()

        balance = await wallet_service.get_native_balance(
            user_id=different_user.id,
            wallet_id=wallet.id,
        )

        assert balance is None

        await session.delete(different_user)
        await session.commit()

        await cleanup_test_data(session)
        
class FakeERC20Reader:
    async def get_balance(
        self,
        token_address: str,
        wallet_address: str,
    ) -> Decimal:
        return Decimal("125.50")


class FakeEthereum:
    async def get_balance(self, address: str) -> int:
        return 1_500_000_000_000_000_000

    def get_erc20_reader(self) -> FakeERC20Reader:
        return FakeERC20Reader()


class FakeBlockchain:
    def __init__(self):
        self.ethereum = FakeEthereum()
        
@pytest.mark.asyncio
async def test_get_token_balance() -> None:
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user, chain = await create_test_user_and_chain(session)

        wallet_service = WalletService(
            session,
            blockchain_service=FakeBlockchain(),
        )

        wallet = await wallet_service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=WALLET_ADDRESS_1,
            label="Token Balance Wallet",
        )

        balance = await wallet_service.get_token_balance(
            user_id=user.id,
            wallet_id=wallet.id,
            token_address="0xA0b86991c6218b36c1d19D4A2e9Eb0cE3606eB48",
            symbol="USDC",
        )

        assert balance is not None
        assert balance.symbol == "USDC"
        assert balance.address == "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        assert balance.balance == Decimal("125.50")

        await cleanup_test_data(session)


@pytest.mark.asyncio
async def test_user_cannot_get_token_balance_of_another_users_wallet() -> None:
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user, chain = await create_test_user_and_chain(session)

        wallet_service = WalletService(
            session,
            blockchain_service=FakeBlockchain(),
        )

        wallet = await wallet_service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address=WALLET_ADDRESS_1,
            label="Protected Token Wallet",
        )

        different_user = User(
            telegram_id=999999999996,
            username="different_user",
            first_name="Different",
            subscription_tier="free",
            is_banned=False,
            created_at=datetime.now(timezone.utc),
        )

        session.add(different_user)
        await session.flush()

        balance = await wallet_service.get_token_balance(
            user_id=different_user.id,
            wallet_id=wallet.id,
            token_address="0xA0b86991c6218b36c1d19D4A2e9Eb0cE3606eB48",
            symbol="USDC",
        )

        assert balance is None

        await session.delete(different_user)
        await session.commit()

        await cleanup_test_data(session)
        
class FakeTransactionProvider:
    async def get_transactions(
        self,
        address: str,
        limit: int = 10,
    ) -> list[WalletTransaction]:
        return [
            WalletTransaction(
                hash="0xtransaction123",
                wallet_address=address,
                from_address=(
                    "0x1111111111111111111111111111111111111111"
                ),
                to_address=(
                    "0x2222222222222222222222222222222222222222"
                ),
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
        ]
        
@pytest.mark.asyncio
async def test_wallet_service_get_transaction_history():
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user, chain = await create_test_user_and_chain(session)

        service = WalletService(
            session,
            blockchain_service=FakeBlockchain(),
            transaction_provider=FakeTransactionProvider(),
        )

        wallet = await service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address="0x1111111111111111111111111111111111111111",
            label="Transaction Test Wallet",
        )

        transactions = await service.get_transaction_history(
            user_id=user.id,
            wallet_id=wallet.id,
            limit=10,
        )

        assert transactions is not None
        assert len(transactions) == 1
        assert transactions[0].hash == "0xtransaction123"
        assert transactions[0].value == Decimal("0.25")
        assert transactions[0].status == "success"

        await cleanup_test_data(session)
        
        
@pytest.mark.asyncio
async def test_wallet_service_transaction_history_respects_wallet_ownership():
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user, chain = await create_test_user_and_chain(session)

        service = WalletService(
            session,
            blockchain_service=FakeBlockchain(),
            transaction_provider=FakeTransactionProvider(),
        )

        wallet = await service.add_wallet(
            user_id=user.id,
            chain_id=chain.id,
            address="0x1111111111111111111111111111111111111111",
            label="Ownership Test Wallet",
        )

        transactions = await service.get_transaction_history(
            user_id=user.id + 999999,
            wallet_id=wallet.id,
            limit=10,
        )

        assert transactions is None

        await cleanup_test_data(session)