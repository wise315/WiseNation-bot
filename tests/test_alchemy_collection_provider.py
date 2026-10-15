import httpx
import pytest

from app.blockchain.providers.alchemy_collection import (
    AlchemyCollectionProvider,
)


class FakeAsyncClient:
    def __init__(self, response):
        self.response = response
        self.requested_url = None
        self.requested_params = None

    async def get(self, url, params=None):
        self.requested_url = url
        self.requested_params = params
        return self.response


@pytest.mark.asyncio
async def test_get_collection_maps_alchemy_response():
    url = (
        "https://eth-mainnet.g.alchemy.com/nft/v3/"
        "test-api-key/getContractMetadata"
    )

    params = {
        "contractAddress": (
            "0x1234567890abcdef1234567890abcdef12345678"
        ),
    }

    response = httpx.Response(
        status_code=200,
        request=httpx.Request(
            "GET",
            url,
            params=params,
        ),
        json={
            "address": (
                "0x1234567890abcdef1234567890abcdef12345678"
            ),
            "name": "Test Collection",
            "symbol": "TEST",
            "tokenType": "ERC721",
            "openseaMetadata": {
                "collectionName": "Test Collection",
                "description": "A test collection.",
                "imageUrl": "https://example.com/image.png",
                "bannerImageUrl": (
                    "https://example.com/banner.png"
                ),
            },
        },
    )

    client = FakeAsyncClient(response)

    provider = AlchemyCollectionProvider(
        api_key="test-api-key",
        client=client,
    )

    collection = await provider.get_collection(
        "0x1234567890abcdef1234567890abcdef12345678"
    )

    assert collection is not None
    assert (
        collection.contract_address
        == "0x1234567890abcdef1234567890abcdef12345678"
    )
    assert collection.name == "Test Collection"
    assert collection.symbol == "TEST"
    assert collection.description == "A test collection."
    assert (
        collection.image_url
        == "https://example.com/image.png"
    )
    assert (
        collection.banner_image_url
        == "https://example.com/banner.png"
    )
    assert collection.token_standard == "ERC721"
    assert collection.blockchain == "ethereum"

    assert client.requested_url == url
    assert client.requested_params == params


@pytest.mark.asyncio
async def test_get_collection_returns_none_without_address():
    url = (
        "https://eth-mainnet.g.alchemy.com/nft/v3/"
        "test-api-key/getContractMetadata"
    )

    response = httpx.Response(
        status_code=200,
        request=httpx.Request("GET", url),
        json={},
    )

    client = FakeAsyncClient(response)

    provider = AlchemyCollectionProvider(
        api_key="test-api-key",
        client=client,
    )

    collection = await provider.get_collection(
        "0x1234567890abcdef1234567890abcdef12345678"
    )

    assert collection is None


@pytest.mark.asyncio
async def test_search_collections_is_not_supported():
    provider = AlchemyCollectionProvider(
        api_key="test-api-key",
    )

    with pytest.raises(
        NotImplementedError,
        match="text-based collection search",
    ):
        await provider.search_collections(
            query="Bored Ape",
        )