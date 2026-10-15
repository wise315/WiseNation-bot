import httpx
import pytest

from app.blockchain.providers.opensea_sale import (
    OpenSeaSaleProvider,
)
from app.blockchain.providers.sale import SaleProvider
from app.schemas.sale import NFTSale
from app.services.collection_service import CollectionService


CONTRACT_ADDRESS = (
    "0x0000000000000000000000000000000000000001"
)


class MockClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def get(
        self,
        url,
        params=None,
        headers=None,
    ):
        self.calls.append(
            {
                "url": url,
                "params": params,
                "headers": headers,
            }
        )

        response = self.responses[url]

        return response


def test_opensea_sale_provider_subclass() -> None:
    provider = OpenSeaSaleProvider(
        api_key="test-key"
    )

    assert isinstance(provider, SaleProvider)


@pytest.mark.asyncio
async def test_opensea_sale_provider() -> None:
    contract_url = (
        "https://api.opensea.io/api/v2/"
        "chain/ethereum/contract/"
        f"{CONTRACT_ADDRESS}"
    )

    events_url = (
        "https://api.opensea.io/api/v2/"
        "events/collection/boredapeyachtclub"
    )

    contract_response = httpx.Response(
        200,
        json={
            "address": CONTRACT_ADDRESS,
            "chain": "ethereum",
            "collection": "boredapeyachtclub",
            "contract_standard": "erc721",
            "name": "Bored Ape Yacht Club",
        },
        request=httpx.Request(
            "GET",
            contract_url,
        ),
    )

    events_response = httpx.Response(
        200,
        json={
            "asset_events": [
                {
                    "event_type": "sale",
                    "event_timestamp": 1726570000,
                    "buyer": (
                        "0x0000000000000000000000000000000000000002"
                    ),
                    "seller": (
                        "0x0000000000000000000000000000000000000003"
                    ),
                    "transaction": "0xabc",
                    "payment": {
                        "quantity": "2500000000000000000",
                        "decimals": 18,
                        "symbol": "ETH",
                        "token_address": (
                            "0x0000000000000000000000000000000000000000"
                        ),
                    },
                    "nft": {
                        "contract": CONTRACT_ADDRESS,
                        "identifier": "123",
                    },
                }
            ]
        },
        request=httpx.Request(
            "GET",
            events_url,
        ),
    )

    client = MockClient(
        {
            contract_url: contract_response,
            events_url: events_response,
        }
    )

    provider = OpenSeaSaleProvider(
        api_key="test-key",
        client=client,
    )

    results = await provider.get_sales(
        contract_address=CONTRACT_ADDRESS,
        limit=10,
    )

    assert len(results) == 1

    sale = results[0]

    assert isinstance(sale, NFTSale)
    assert sale.contract_address == CONTRACT_ADDRESS
    assert sale.token_id == "123"
    assert sale.price == 2.5
    assert sale.currency == "ETH"
    assert sale.buyer == (
        "0x0000000000000000000000000000000000000002"
    )
    assert sale.seller == (
        "0x0000000000000000000000000000000000000003"
    )
    assert sale.marketplace == "OpenSea"
    assert sale.transaction_hash == "0xabc"

    assert sale.timestamp is not None

    assert client.calls[0]["headers"]["x-api-key"] == "test-key"

    assert client.calls[1]["params"] == {
        "event_type": "sale",
        "limit": 10,
    }


@pytest.mark.asyncio
async def test_opensea_sale_provider_collection_not_found() -> None:
    contract_url = (
        "https://api.opensea.io/api/v2/"
        "chain/ethereum/contract/"
        f"{CONTRACT_ADDRESS}"
    )

    contract_response = httpx.Response(
        404,
        json={
            "detail": "Collection not found",
        },
        request=httpx.Request(
            "GET",
            contract_url,
        ),
    )

    client = MockClient(
        {
            contract_url: contract_response,
        }
    )

    provider = OpenSeaSaleProvider(
        api_key="test-key",
        client=client,
    )

    results = await provider.get_sales(
        contract_address=CONTRACT_ADDRESS,
        limit=10,
    )

    assert results == []


@pytest.mark.asyncio
async def test_opensea_sale_provider_empty_sales() -> None:
    contract_url = (
        "https://api.opensea.io/api/v2/"
        "chain/ethereum/contract/"
        f"{CONTRACT_ADDRESS}"
    )

    events_url = (
        "https://api.opensea.io/api/v2/"
        "events/collection/boredapeyachtclub"
    )

    contract_response = httpx.Response(
        200,
        json={
            "address": CONTRACT_ADDRESS,
            "chain": "ethereum",
            "collection": "boredapeyachtclub",
            "contract_standard": "erc721",
            "name": "Bored Ape Yacht Club",
        },
        request=httpx.Request(
            "GET",
            contract_url,
        ),
    )

    events_response = httpx.Response(
        200,
        json={
            "asset_events": [],
        },
        request=httpx.Request(
            "GET",
            events_url,
        ),
    )

    client = MockClient(
        {
            contract_url: contract_response,
            events_url: events_response,
        }
    )

    provider = OpenSeaSaleProvider(
        api_key="test-key",
        client=client,
    )

    results = await provider.get_sales(
        contract_address=CONTRACT_ADDRESS,
        limit=10,
    )

    assert results == []


@pytest.mark.asyncio
async def test_collection_service_get_sales() -> None:
    class MockSaleProvider:
        async def get_sales(
            self,
            contract_address: str,
            limit: int = 10,
        ) -> list[NFTSale]:
            return [
                NFTSale(
                    contract_address=contract_address,
                    token_id="456",
                    price=1.75,
                    currency="ETH",
                    buyer=(
                        "0x0000000000000000000000000000000000000002"
                    ),
                    seller=(
                        "0x0000000000000000000000000000000000000003"
                    ),
                    marketplace="OpenSea",
                    transaction_hash="0xdef",
                )
            ]

    service = CollectionService(
        collection_provider=None,
        sale_provider=MockSaleProvider(),
    )

    results = await service.get_sales(
        contract_address=CONTRACT_ADDRESS,
        limit=10,
    )

    assert len(results) == 1
    assert results[0].token_id == "456"
    assert results[0].price == 1.75
    assert results[0].currency == "ETH"
    assert results[0].marketplace == "OpenSea"