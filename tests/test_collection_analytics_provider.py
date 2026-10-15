import pytest
import httpx

from app.blockchain.providers.opensea_analytics import (
    OpenSeaAnalyticsProvider,
)


CONTRACT_ADDRESS = (
    "0x0000000000000000000000000000000000000001"
)


class MockAsyncClient:
    def __init__(self):
        self.calls = []

    async def get(self, url, **kwargs):
        self.calls.append(
            {
                "url": url,
                "kwargs": kwargs,
            }
        )

        if "/chain/ethereum/contract/" in url:
            return httpx.Response(
                200,
                json={
                    "collection": "test-collection",
                    "total_supply": 10_000,
                    "unique_item_count": 10_000,
                },
                request=httpx.Request("GET", url),
            )

        if "/collections/test-collection/stats" in url:
            return httpx.Response(
                200,
                json={
                    "intervals": [
                        {
                            "interval": "one_day",
                            "sales": 17,
                            "volume": 42.35,
                            "volume_symbol": "ETH",
                        },
                        {
                            "interval": "seven_days",
                            "sales": 74,
                            "volume": 183.20,
                            "volume_symbol": "ETH",
                        },
                        {
                            "interval": "thirty_days",
                            "sales": 291,
                            "volume": 721.50,
                            "volume_symbol": "ETH",
                        },
                    ],
                    "total": {
                        "floor_price": 8.5,
                        "floor_price_symbol": "ETH",
                        "num_owners": 3421,
                        "sales": 5842,
                        "volume": 12450.0,
                        "volume_symbol": "ETH",
                    },
                },
                request=httpx.Request("GET", url),
            )

        return httpx.Response(
            404,
            request=httpx.Request("GET", url),
        )


@pytest.mark.asyncio
async def test_get_collection_analytics() -> None:
    client = MockAsyncClient()

    provider = OpenSeaAnalyticsProvider(
        api_key="test-api-key",
        client=client,
    )

    analytics = await provider.get_analytics(
        contract_address=CONTRACT_ADDRESS
    )

    assert analytics is not None

    assert analytics.collection_slug == "test-collection"
    assert analytics.contract_address == CONTRACT_ADDRESS

    assert analytics.floor_price == 8.5
    assert analytics.floor_price_currency == "ETH"

    assert analytics.one_day_volume == 42.35
    assert analytics.one_day_volume_currency == "ETH"
    assert analytics.one_day_sales == 17

    assert analytics.seven_day_volume == 183.20
    assert analytics.seven_day_volume_currency == "ETH"
    assert analytics.seven_day_sales == 74

    assert analytics.thirty_day_volume == 721.50
    assert analytics.thirty_day_volume_currency == "ETH"
    assert analytics.thirty_day_sales == 291

    assert analytics.total_volume == 12450.0
    assert analytics.total_volume_currency == "ETH"
    assert analytics.total_sales == 5842

    assert analytics.num_owners == 3421
    assert analytics.total_supply == 10_000
    assert analytics.unique_item_count == 10_000


@pytest.mark.asyncio
async def test_get_collection_analytics_returns_none_when_collection_missing() -> None:
    class MissingCollectionClient:
        async def get(self, url, **kwargs):
            return httpx.Response(
                404,
                request=httpx.Request("GET", url),
            )

    provider = OpenSeaAnalyticsProvider(
        api_key="test-api-key",
        client=MissingCollectionClient(),
    )

    analytics = await provider.get_analytics(
        contract_address=CONTRACT_ADDRESS
    )

    assert analytics is None


@pytest.mark.asyncio
async def test_provider_uses_opensea_api_key() -> None:
    client = MockAsyncClient()

    provider = OpenSeaAnalyticsProvider(
        api_key="my-test-key",
        client=client,
    )

    await provider.get_analytics(
        contract_address=CONTRACT_ADDRESS
    )

    assert len(client.calls) == 2

    for call in client.calls:
        assert call["kwargs"]["headers"]["x-api-key"] == (
            "my-test-key"
        )


@pytest.mark.asyncio
async def test_provider_parses_stats_types() -> None:
    provider = OpenSeaAnalyticsProvider(
        api_key="test-api-key",
        client=MockAsyncClient(),
    )

    analytics = await provider.get_analytics(
        contract_address=CONTRACT_ADDRESS
    )

    assert analytics is not None
    assert isinstance(analytics.floor_price, float)
    assert isinstance(analytics.one_day_sales, int)
    assert isinstance(analytics.num_owners, int)