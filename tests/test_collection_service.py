import pytest

from app.schemas.collection import NFTCollection
from app.services.collection_service import CollectionService


class FakeCollectionProvider:
    async def get_collection(
        self,
        identifier: str,
    ) -> NFTCollection | None:
        if identifier == "0xvalid":
            return NFTCollection(
                contract_address="0xvalid",
                name="Test Collection",
                symbol="TEST",
                blockchain="ethereum",
            )

        return None

    async def search_collections(
        self,
        query: str,
        limit: int = 10,
    ) -> list[NFTCollection]:
        return [
            NFTCollection(
                contract_address="0x123",
                name="Test Collection",
                symbol="TEST",
                blockchain="ethereum",
            )
        ][:limit]


@pytest.mark.asyncio
async def test_get_collection():
    service = CollectionService(
        collection_provider=FakeCollectionProvider(),
    )

    collection = await service.get_collection(
        identifier="0xvalid",
    )

    assert collection is not None
    assert collection.name == "Test Collection"
    assert collection.symbol == "TEST"


@pytest.mark.asyncio
async def test_get_collection_returns_none():
    service = CollectionService(
        collection_provider=FakeCollectionProvider(),
    )

    collection = await service.get_collection(
        identifier="0xmissing",
    )

    assert collection is None


@pytest.mark.asyncio
async def test_search_collections():
    service = CollectionService(
        collection_provider=FakeCollectionProvider(),
    )

    collections = await service.search_collections(
        query="Test",
        limit=10,
    )

    assert len(collections) == 1
    assert collections[0].name == "Test Collection"