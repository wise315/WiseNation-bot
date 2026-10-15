from decimal import Decimal

import pytest

from app.database.session import AsyncSessionLocal
from app.schemas.nft import WalletNFT
from app.services.user_service import UserService
from app.services.wallet_service import WalletService


class FakeNFTProvider:
    async def get_nfts(
        self,
        address: str,
        limit: int = 20,
    ) -> list[WalletNFT]:
        return [
            WalletNFT(
                contract_address=(
                    "0x1234567890abcdef1234567890abcdef12345678"
                ),
                token_id="123",
                collection_name="Test Collection",
                name="Test NFT #123",
                image_url="https://example.com/nft.png",
                token_standard="ERC721",
                wallet_address=address,
            )
        ]


@pytest.mark.asyncio
async def test_get_nfts_returns_wallet_nfts():
    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=990000004,
            username="nft_test_user",
            first_name="NFT",
        )

        wallet_service = WalletService(
            session,
            nft_provider=FakeNFTProvider(),
        )

        wallet = await wallet_service.add_wallet(
            user_id=user.id,
            chain_id=1,
            address=(
                "0x0000000000000000000000000000000000000003"
            ),
            label="NFT Test Wallet",
        )

        nfts = await wallet_service.get_nfts(
            user_id=user.id,
            wallet_id=wallet.id,
            limit=20,
        )

        assert nfts is not None
        assert len(nfts) == 1

        nft = nfts[0]

        assert nft.token_id == "123"
        assert nft.collection_name == "Test Collection"
        assert nft.name == "Test NFT #123"
        assert nft.token_standard == "ERC721"
        assert nft.wallet_address == wallet.address


@pytest.mark.asyncio
async def test_get_nfts_rejects_other_users_wallet():
    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        owner, _ = await user_service.get_or_create_user(
            telegram_id=990000005,
            username="nft_owner",
            first_name="Owner",
        )

        other_user, _ = await user_service.get_or_create_user(
            telegram_id=990000006,
            username="nft_other",
            first_name="Other",
        )

        wallet_service = WalletService(
            session,
            nft_provider=FakeNFTProvider(),
        )

        wallet = await wallet_service.add_wallet(
            user_id=owner.id,
            chain_id=1,
            address=(
                "0x0000000000000000000000000000000000000004"
            ),
            label="Owner NFT Wallet",
        )

        nfts = await wallet_service.get_nfts(
            user_id=other_user.id,
            wallet_id=wallet.id,
            limit=20,
        )

        assert nfts is None


@pytest.mark.asyncio
async def test_get_nfts_requires_provider():
    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=990000007,
            username="nft_no_provider",
            first_name="No Provider",
        )

        wallet_service = WalletService(session)

        wallet = await wallet_service.add_wallet(
            user_id=user.id,
            chain_id=1,
            address=(
                "0x0000000000000000000000000000000000000005"
            ),
            label="No Provider Wallet",
        )

        with pytest.raises(
            RuntimeError,
            match="NFT provider is not configured",
        ):
            await wallet_service.get_nfts(
                user_id=user.id,
                wallet_id=wallet.id,
                limit=20,
            )