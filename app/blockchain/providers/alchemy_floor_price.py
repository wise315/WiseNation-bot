from datetime import datetime
from typing import Any

import httpx

from app.blockchain.providers.floor_price import FloorPriceProvider
from app.schemas.floor_price import CollectionFloorPrice


class AlchemyFloorPriceProvider(FloorPriceProvider):
    BASE_URL = "https://eth-mainnet.g.alchemy.com/nft/v3"

    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key
        self.client = client

    async def get_floor_prices(
        self,
        contract_address: str,
    ) -> list[CollectionFloorPrice]:
        url = f"{self.BASE_URL}/{self.api_key}/getFloorPrice"
        params = {
            "contractAddress": contract_address,
        }

        should_close_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=15.0)

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()

            data: dict[str, Any] = response.json()
            results: list[CollectionFloorPrice] = []

            for marketplace, marketplace_data in data.items():
                if not isinstance(marketplace_data, dict):
                    continue

                retrieved_at = marketplace_data.get("retrievedAt")

                parsed_retrieved_at = None

                if retrieved_at:
                    try:
                        parsed_retrieved_at = datetime.fromisoformat(
                            retrieved_at.replace("Z", "+00:00")
                        )
                    except ValueError:
                        parsed_retrieved_at = None

                results.append(
                    CollectionFloorPrice(
                        marketplace=marketplace,
                        floor_price=marketplace_data.get("floorPrice"),
                        currency=marketplace_data.get("priceCurrency"),
                        collection_url=marketplace_data.get("collectionUrl"),
                        retrieved_at=parsed_retrieved_at,
                        error=marketplace_data.get("error"),
                    )
                )

            return results

        finally:
            if should_close_client:
                await client.aclose()