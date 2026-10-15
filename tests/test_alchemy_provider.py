import httpx
import pytest

from app.blockchain.providers.alchemy import AlchemyNFTProvider


class FakeAsyncClient:
    def __init__(self):
        self.request_url = None
        self.request_params = None

    async def get(self, url, params=None):
        self.request_url = url
        self.request_params = params

        request = httpx.Request(
            "GET",
            url,
            params=params,
        )

        return httpx.Response(
            status_code=200,
            request=request,
            json={
                "ownedNfts": [
                    {
                        "contract": {
                            "address": (
                                "0x1234567890abcdef1234567890abcdef12345678"
                            ),
                            "name": "Test Collection",
                            "tokenType": "ERC721",
                        },
                        "tokenId": "123",
                        "tokenType": "ERC721",
                        "name": "Test NFT #123",
                        "image": {
                            "cachedUrl": (
                                "https://example.com/nft.png"
                            ),
                        },
                        "collection": {
                            "name": "Test Collection",
                        },
                    }
                ]
            },
        )

@pytest.mark.asyncio
async def test_alchemy_provider_returns_nfts():
    client = FakeAsyncClient()

    provider = AlchemyNFTProvider(
        api_key="test-api-key",
        client=client,
    )

    wallet_address = (
        "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
    )

    nfts = await provider.get_nfts(
        address=wallet_address,
        limit=10,
    )

    assert len(nfts) == 1

    nft = nfts[0]

    assert (
        nft.contract_address
        == "0x1234567890abcdef1234567890abcdef12345678"
    )
    assert nft.token_id == "123"
    assert nft.collection_name == "Test Collection"
    assert nft.name == "Test NFT #123"
    assert nft.image_url == "https://example.com/nft.png"
    assert nft.token_standard == "ERC721"
    assert nft.wallet_address == wallet_address


@pytest.mark.asyncio
async def test_alchemy_provider_sends_correct_request():
    client = FakeAsyncClient()

    provider = AlchemyNFTProvider(
        api_key="test-api-key",
        client=client,
    )

    wallet_address = (
        "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
    )

    await provider.get_nfts(
        address=wallet_address,
        limit=15,
    )

    assert client.request_url == (
        "https://eth-mainnet.g.alchemy.com/nft/v3/"
        "test-api-key/getNFTsForOwner"
    )

    assert client.request_params == {
        "owner": wallet_address,
        "pageSize": 15,
        "withMetadata": "true",
    }