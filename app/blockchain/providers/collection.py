from abc import ABC, abstractmethod

from app.schemas.collection import NFTCollection


class CollectionProvider(ABC):
    @abstractmethod
    async def get_collection(
        self,
        identifier: str,
    ) -> NFTCollection | None:
        """Return a collection by contract address or provider identifier."""
        raise NotImplementedError

    @abstractmethod
    async def search_collections(
        self,
        query: str,
        limit: int = 10,
    ) -> list[NFTCollection]:
        """Search for NFT collections."""
        raise NotImplementedError