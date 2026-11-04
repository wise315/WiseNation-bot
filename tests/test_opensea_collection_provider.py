
import httpx
import pytest

from app.blockchain.providers.opensea_collection import (
    OpenSeaCollectionProvider,
)


CONTRACT_ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"


class FakeAsyncClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def get(self, url, params=None, headers=None):
        self.calls.append({
            "url": url,
            "params": params,
            "headers": headers,
        })
        return self.responses.pop(0)


def make_response(url, data, status_code=200):
    return httpx.Response(
        status_code=status_code,
        request=httpx.Request("GET", url),
        json=data,
    )


@pytest.mark.asyncio
async def test_get_collection_maps_opensea_response():
    contract_url = (
        "https://api.opensea.io/api/v2/chain/ethereum/contract/"
        f"{CONTRACT_ADDRESS}"
    )
    collection_url = (
        "https://api.opensea.io/api/v2/collections/test-collection"
    )

    client = FakeAsyncClient([
        make_response(
            contract_url,
            {
                "address": CONTRACT_ADDRESS,
                "chain": "ethereum",
                "collection": "test-collection",
                "contract_standard": "erc721",
                "name": "Test Collection",
            },
        ),
        make_response(
            collection_url,
            {
                "name": "Test Collection",
                "description": "A test collection.",
                "image_url": "https://example.com/image.png",
                "banner_image_url": "https://example.com/banner.png",
                "contracts": [
                    {
                        "address": CONTRACT_ADDRESS,
                        "chain": "ethereum",
                    }
                ],
            },
        ),
    ])

    provider = OpenSeaCollectionProvider(
        api_key="test-api-key",
        client=client,
    )

    collection = await provider.get_collection(CONTRACT_ADDRESS)

    assert collection is not None
    assert collection.contract_address == CONTRACT_ADDRESS
    assert collection.name == "Test Collection"
    assert collection.symbol is None
    assert collection.description == "A test collection."
    assert collection.image_url == "https://example.com/image.png"
    assert collection.banner_image_url == "https://example.com/banner.png"
    assert collection.token_standard == "erc721"
    assert collection.blockchain == "ethereum"

    assert len(client.calls) == 2
    assert client.calls[0]["url"] == contract_url
    assert client.calls[1]["url"] == collection_url
    assert client.calls[0]["headers"]["x-api-key"] == "test-api-key"


@pytest.mark.asyncio
async def test_get_collection_returns_none_when_contract_not_found():
    contract_url = (
        "https://api.opensea.io/api/v2/chain/ethereum/contract/"
        f"{CONTRACT_ADDRESS}"
    )

    client = FakeAsyncClient([
        make_response(contract_url, {}, status_code=404),
    ])

    provider = OpenSeaCollectionProvider(
        api_key="test-api-key",
        client=client,
    )

    collection = await provider.get_collection(CONTRACT_ADDRESS)

    assert collection is None
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_get_collection_returns_none_without_contract_address():
    contract_url = (
        "https://api.opensea.io/api/v2/chain/ethereum/contract/"
        f"{CONTRACT_ADDRESS}"
    )

    client = FakeAsyncClient([
        make_response(contract_url, {}),
    ])

    provider = OpenSeaCollectionProvider(
        api_key="test-api-key",
        client=client,
    )

    collection = await provider.get_collection(CONTRACT_ADDRESS)

    assert collection is None


@pytest.mark.asyncio
async def test_search_collections_returns_collection_details():
    search_url = "https://api.opensea.io/api/v2/search"
    collection_url = (
        "https://api.opensea.io/api/v2/collections/test-collection"
    )

    client = FakeAsyncClient([
        make_response(
            search_url,
            {
                "results": [
                    {
                        "collection": {
                            "collection": "test-collection",
                        }
                    }
                ]
            },
        ),
        make_response(
            collection_url,
            {
                "name": "Test Collection",
                "description": "A searchable collection.",
                "image_url": "https://example.com/image.png",
                "contracts": [
                    {
                        "address": CONTRACT_ADDRESS,
                        "chain": "ethereum",
                    }
                ],
            },
        ),
    ])

    provider = OpenSeaCollectionProvider(
        api_key="test-api-key",
        client=client,
    )

    collections = await provider.search_collections(
        query="Test Collection",
        limit=10,
    )

    assert len(collections) == 1
    assert collections[0].name == "Test Collection"
    assert collections[0].contract_address == CONTRACT_ADDRESS
    assert collections[0].description == "A searchable collection."

    assert client.calls[0]["url"] == search_url
    assert client.calls[0]["params"]["query"] == "Test Collection"
    assert client.calls[0]["params"]["limit"] == 10
    assert client.calls[0]["headers"]["x-api-key"] == "test-api-key"
