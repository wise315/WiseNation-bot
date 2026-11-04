
import httpx
import pytest

from app.blockchain.providers.opensea_nft import OpenSeaNFTProvider


WALLET_ADDRESS = "0x0000000000000000000000000000000000000001"

NFT_RESPONSE = {
    "collection": "test-collection",
    "contract": "0x1234567890abcdef1234567890abcdef12345678",
    "identifier": "123",
    "name": "Test NFT #123",
    "image_url": "https://example.com/nft.png",
    "token_standard": "erc721",
}


@pytest.mark.asyncio
async def test_get_nfts_returns_wallet_nfts():
    async def handler(request):
        assert request.url.path.endswith(
            f"/account/{WALLET_ADDRESS}/nfts"
        )
        assert request.headers["x-api-key"] == "test-key"
        assert request.url.params["limit"] == "20"

        return httpx.Response(
            200,
            json={
                "nfts": [NFT_RESPONSE],
                "next": None,
            },
        )

    client = httpx.AsyncClient(
    transport=httpx.MockTransport(handler),
    base_url=OpenSeaNFTProvider.BASE_URL,
    headers={
        "x-api-key": "test-key",
        "accept": "application/json",
    },
)

    provider = OpenSeaNFTProvider(
        api_key="test-key",
        client=client,
    )

    try:
        nfts = await provider.get_nfts(WALLET_ADDRESS)

        assert len(nfts) == 1

        nft = nfts[0]

        assert nft.contract_address == NFT_RESPONSE["contract"]
        assert nft.token_id == "123"
        assert nft.collection_name == "test-collection"
        assert nft.name == "Test NFT #123"
        assert nft.image_url == "https://example.com/nft.png"
        assert nft.token_standard == "ERC721"
        assert nft.wallet_address == WALLET_ADDRESS

    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_get_nfts_handles_missing_metadata():
    async def handler(request):
        return httpx.Response(
            200,
            json={
                "nfts": [
                    {
                        "contract": NFT_RESPONSE["contract"],
                        "identifier": "456",
                        "collection": "test-collection",
                        "token_standard": "erc1155",
                    },
                    {
                        "collection": "invalid-nft",
                        "identifier": "789",
                    },
                ],
                "next": None,
            },
        )

    client = httpx.AsyncClient(
    transport=httpx.MockTransport(handler),
    base_url=OpenSeaNFTProvider.BASE_URL,
    headers={
        "x-api-key": "test-key",
        "accept": "application/json",
    },
)
    provider = OpenSeaNFTProvider(
        api_key="test-key",
        client=client,
    )

    try:
        nfts = await provider.get_nfts(WALLET_ADDRESS)

        assert len(nfts) == 1
        assert nfts[0].token_id == "456"
        assert nfts[0].name is None
        assert nfts[0].image_url is None
        assert nfts[0].token_standard == "ERC1155"

    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_get_nfts_supports_pagination():
    requests = []

    async def handler(request):
        requests.append(request)

        if len(requests) == 1:
            return httpx.Response(
                200,
                json={
                    "nfts": [
                        {
                            **NFT_RESPONSE,
                            "identifier": "1",
                        }
                    ],
                    "next": "next-page-token",
                },
            )

        assert request.url.params["next"] == "next-page-token"

        return httpx.Response(
            200,
            json={
                "nfts": [
                    {
                        **NFT_RESPONSE,
                        "identifier": "2",
                    }
                ],
                "next": None,
            },
        )

    client = httpx.AsyncClient(
    transport=httpx.MockTransport(handler),
    base_url=OpenSeaNFTProvider.BASE_URL,
    headers={
        "x-api-key": "test-key",
        "accept": "application/json",
    },
)

    provider = OpenSeaNFTProvider(
        api_key="test-key",
        client=client,
    )

    try:
        nfts = await provider.get_nfts(
            WALLET_ADDRESS,
            limit=2,
        )

        assert len(requests) == 2
        assert len(nfts) == 2
        assert nfts[0].token_id == "1"
        assert nfts[1].token_id == "2"

    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_get_nfts_propagates_api_errors():
    async def handler(request):
        return httpx.Response(
            401,
            json={"detail": "Invalid API key"},
        )

    client = httpx.AsyncClient(
    transport=httpx.MockTransport(handler),
    base_url=OpenSeaNFTProvider.BASE_URL,
    headers={
        "x-api-key": "test-key",
        "accept": "application/json",
    },
)

    provider = OpenSeaNFTProvider(
        api_key="test-key",
        client=client,
    )

    try:
        with pytest.raises(httpx.HTTPStatusError):
            await provider.get_nfts(WALLET_ADDRESS)

    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_get_nfts_rejects_invalid_limit():
    provider = OpenSeaNFTProvider(api_key="test-key")

    with pytest.raises(
        ValueError,
        match="NFT limit must be at least 1",
    ):
        await provider.get_nfts(
            WALLET_ADDRESS,
            limit=0,
        )


def test_provider_rejects_empty_api_key():
    with pytest.raises(
        ValueError,
        match="OpenSea API key is required",
    ):
        OpenSeaNFTProvider(api_key="")

