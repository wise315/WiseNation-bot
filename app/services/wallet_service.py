from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.blockchain.address import normalize_ethereum_address
from app.blockchain.providers.nft import NFTProvider
from app.blockchain.providers.transaction import TransactionHistoryProvider
from app.blockchain.service import BlockchainService
from app.blockchain.utils import wei_to_eth
from app.database.models import Wallet
from app.repositories.wallets import WalletRepository
from app.schemas.nft import WalletNFT
from app.schemas.token import TokenBalance
from app.schemas.transaction import WalletTransaction


class WalletService:
    def __init__(
        self,
        session: AsyncSession,
        blockchain_service: BlockchainService | None = None,
        transaction_provider: TransactionHistoryProvider | None = None,
        nft_provider: NFTProvider | None = None,
    ):
        self.session = session
        self.repository = WalletRepository(session)
        self.blockchain = blockchain_service or BlockchainService()
        self.transaction_provider = transaction_provider
        self.nft_provider = nft_provider

    async def get_wallet(
        self,
        user_id: int,
        wallet_id: int,
    ) -> Wallet | None:
        wallet = await self.repository.get_by_id(wallet_id)

        if wallet is None:
            return None

        if wallet.user_id != user_id:
            return None

        return wallet

    async def get_native_balance(
        self,
        user_id: int,
        wallet_id: int,
    ) -> Decimal | None:
        wallet = await self.get_wallet(
            user_id=user_id,
            wallet_id=wallet_id,
        )

        if wallet is None:
            return None

        balance_wei = await self.blockchain.ethereum.get_balance(
            wallet.address
        )

        return wei_to_eth(balance_wei)

    async def get_token_balance(
        self,
        user_id: int,
        wallet_id: int,
        token_address: str,
        symbol: str,
    ) -> TokenBalance | None:
        wallet = await self.get_wallet(
            user_id=user_id,
            wallet_id=wallet_id,
        )

        if wallet is None:
            return None

        reader = self.blockchain.ethereum.get_erc20_reader()

        balance = await reader.get_balance(
            token_address=token_address,
            wallet_address=wallet.address,
        )

        return TokenBalance(
            symbol=symbol,
            address=normalize_ethereum_address(token_address),
            balance=balance,
        )

    async def get_transaction_history(
        self,
        user_id: int,
        wallet_id: int,
        limit: int = 10,
    ) -> list[WalletTransaction] | None:
        wallet = await self.get_wallet(
            user_id=user_id,
            wallet_id=wallet_id,
        )

        if wallet is None:
            return None

        if self.transaction_provider is None:
            raise RuntimeError(
                "Transaction history provider is not configured."
            )

        return await self.transaction_provider.get_transactions(
            address=wallet.address,
            limit=limit,
        )

    async def get_nfts(
        self,
        user_id: int,
        wallet_id: int,
        limit: int = 20,
    ) -> list[WalletNFT] | None:
        wallet = await self.get_wallet(
            user_id=user_id,
            wallet_id=wallet_id,
        )

        if wallet is None:
            return None

        if self.nft_provider is None:
            raise RuntimeError(
                "NFT provider is not configured."
            )

        return await self.nft_provider.get_nfts(
            address=wallet.address,
            limit=limit,
        )

    async def get_user_wallets(
        self,
        user_id: int,
    ) -> list[Wallet]:
        return await self.repository.get_by_user_id(user_id)

    async def get_default_wallet(
        self,
        user_id: int,
    ) -> Wallet | None:
        return await self.repository.get_default_by_user_id(user_id)

    async def add_wallet(
        self,
        user_id: int,
        chain_id: int,
        address: str,
        label: str | None = None,
        wallet_type: str = "watch_only",
        encrypted_private_key: str | None = None,
    ) -> Wallet:
        normalized_address = address.strip()

        existing_wallets = await self.repository.get_by_user_id(user_id)
        is_first_wallet = len(existing_wallets) == 0

        wallet = await self.repository.create(
            user_id=user_id,
            chain_id=chain_id,
            address=normalized_address,
            label=label.strip() if label else None,
            wallet_type=wallet_type,
            encrypted_private_key=encrypted_private_key,
            is_default=is_first_wallet,
        )

        await self.session.commit()
        return wallet

    async def set_default_wallet(
        self,
        user_id: int,
        wallet_id: int,
    ) -> Wallet | None:
        wallet = await self.repository.get_by_id(wallet_id)

        if wallet is None:
            return None

        if wallet.user_id != user_id:
            return None

        user_wallets = await self.repository.get_by_user_id(user_id)

        for user_wallet in user_wallets:
            user_wallet.is_default = user_wallet.id == wallet_id

        await self.session.commit()
        return wallet

    async def remove_wallet(
        self,
        user_id: int,
        wallet_id: int,
    ) -> bool:
        wallet = await self.repository.get_by_id(wallet_id)

        if wallet is None:
            return False

        if wallet.user_id != user_id:
            return False

        was_default = wallet.is_default

        deleted = await self.repository.delete(wallet_id)

        if not deleted:
            return False

        if was_default:
            remaining_wallets = await self.repository.get_by_user_id(user_id)

            if remaining_wallets:
                remaining_wallets[0].is_default = True

        await self.session.commit()
        return True