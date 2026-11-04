from app.blockchain.providers.floor_price_factory import (
    create_floor_price_provider,
)
from app.core.config import get_settings
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest

from app.blockchain.providers.floor_price import FloorPriceProvider
from app.blockchain.providers.opensea_floor_price import (
    OpenSeaFloorPriceProvider,
)
from app.schemas.floor_price import CollectionFloorPrice
from app.services.collection_service import CollectionService


CONTRACT_ADDRESS = "0x0000000000000000000000000000000000000001"


def test_collection_floor_price_schema():
    floor_price = CollectionFloorPrice(
        marketplace="OpenSea",
        floor_price=1.25,
        currency="ETH",
        collection_url="https://opensea.io/collection/example",
        retrieved_at=datetime.now(timezone.utc),
    )

    assert floor_price.marketplace == "OpenSea"
    assert floor_price.floor_price == 1.25
    assert floor_price.currency == "ETH"


def test_floor_price_provider_is_abstract():
    assert FloorPriceProvider.__abstractmethods__ == {
        "get_floor_prices"
    }


def test_opensea_floor_price_provider_implements_interface():
    assert issubclass(
        OpenSeaFloorPriceProvider,
        FloorPriceProvider,
    )


@pytest.mark.asyncio
async def test_opensea_floor_price_provider():
    requests = []

    async def handler(request):
        requests.append(request)

        if request.url.path.endswith(
            f"/contract/{CONTRACT_ADDRESS}"
        ):
            return httpx.Response(
                200,
                json={
                    "collection": "example",
                    "total_supply": 100,
                },
            )

        if request.url.path.endswith(
            "/collections/example/stats"
        ):
            return httpx.Response(
                200,
                json={
                    "total": {
                        "floor_price": 1.25,
                        "floor_price_symbol": "ETH",
                    },
                    "intervals": [],
                },
            )

        return httpx.Response(404)

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    )

    provider = OpenSeaFloorPriceProvider(
        api_key="test-key",
        client=client,
    )

    try:
        results = await provider.get_floor_prices(
            contract_address=CONTRACT_ADDRESS,
        )

        assert len(results) == 1

        result = results[0]

        assert result.marketplace == "OpenSea"
        assert result.floor_price == 1.25
        assert result.currency == "ETH"
        assert result.collection_url == (
            "https://opensea.io/collection/example"
        )
        assert result.retrieved_at is not None

        assert len(requests) == 2
        assert all(
            request.headers["x-api-key"] == "test-key"
            for request in requests
        )

    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_opensea_floor_price_returns_empty_for_missing_collection():
    async def handler(request):
        return httpx.Response(404)

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    )

    provider = OpenSeaFloorPriceProvider(
        api_key="test-key",
        client=client,
    )

    try:
        results = await provider.get_floor_prices(
            contract_address=CONTRACT_ADDRESS,
        )

        assert results == []

    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_collection_service_get_floor_prices():
    provider = AsyncMock()

    provider.get_floor_prices.return_value = [
        CollectionFloorPrice(
            marketplace="OpenSea",
            floor_price=2.5,
            currency="ETH",
        )
    ]

    service = CollectionService(
        collection_provider=AsyncMock(),
        floor_price_provider=provider,
    )

    results = await service.get_floor_prices(
        contract_address=CONTRACT_ADDRESS,
    )

    assert len(results) == 1
    assert results[0].marketplace == "OpenSea"
    assert results[0].floor_price == 2.5

    provider.get_floor_prices.assert_awaited_once_with(
        contract_address=CONTRACT_ADDRESS
    )

def test_create_floor_price_provider_with_api_key(monkeypatch):
    settings = get_settings()

    monkeypatch.setattr(
        settings,
        "opensea_api_key",
        "test-opensea-key",
    )

    provider = create_floor_price_provider()

    assert isinstance(provider, OpenSeaFloorPriceProvider)
    assert (
        provider.analytics_provider.api_key
        == "test-opensea-key"
    )


def test_create_floor_price_provider_without_api_key(monkeypatch):
    settings = get_settings()

    monkeypatch.setattr(
        settings,
        "opensea_api_key",
        "",
    )

    with pytest.raises(
        RuntimeError,
        match="OpenSea API key is not configured",
    ):
        create_floor_price_provider()