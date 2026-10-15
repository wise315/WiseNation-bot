from abc import ABC, abstractmethod

from app.schemas.nft import WalletNFT


class NFTProvider(ABC):
    @abstractmethod
    async def get_nfts(
        self,
        address: str,
        limit: int = 20,
    ) -> list[WalletNFT]:
        """Return NFTs currently held by a wallet address."""
        raise NotImplementedError