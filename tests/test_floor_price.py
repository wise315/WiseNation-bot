from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest

from app.blockchain.providers.alchemy_floor_price import (
    AlchemyFloorPriceProvider,
)
from app.blockchain.providers.floor_price import FloorPriceProvider
from app.schemas.floor_price import CollectionFloorPrice
from app.services.collection_service import CollectionService


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
    assert issubclass(
        AlchemyFloorPriceProvider,
        FloorPriceProvider,
    )


@pytest.mark.asyncio
async def test_alchemy_floor_price_provider():
    response = httpx.Response(
        200,
        json={
            "OpenSea": {
                "floorPrice": 1.25,
                "priceCurrency": "ETH",
                "collectionUrl": "https://opensea.io/collection/example",
                "retrievedAt": "2026-09-17T12:00:00Z",
            },
            "LooksRare": {
                "floorPrice": 1.10,
                "priceCurrency": "ETH",
                "collectionUrl": "https://looksrare.org/collections/example",
                "retrievedAt": "2026-09-17T12:01:00Z",
            },
        },
        request=httpx.Request(
            "GET",
            "https://eth-mainnet.g.alchemy.com/nft/v3/test-key/getFloorPrice",
        ),
    )

    client = AsyncMock(spec=httpx.AsyncClient)
    client.get.return_value = response

    provider = AlchemyFloorPriceProvider(
        api_key="test-key",
        client=client,
    )

    results = await provider.get_floor_prices(
        contract_address="0x0000000000000000000000000000000000000001"
    )

    assert len(results) == 2

    assert results[0].marketplace == "OpenSea"
    assert results[0].floor_price == 1.25
    assert results[0].currency == "ETH"

    assert results[1].marketplace == "LooksRare"
    assert results[1].floor_price == 1.10

    client.get.assert_awaited_once()


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
        contract_address="0x0000000000000000000000000000000000000001"
    )

    assert len(results) == 1
    assert results[0].marketplace == "OpenSea"
    assert results[0].floor_price == 2.5

    provider.get_floor_prices.assert_awaited_once_with(
        contract_address="0x0000000000000000000000000000000000000001"
    )