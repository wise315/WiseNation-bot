
from datetime import datetime, timezone

import httpx

from app.blockchain.providers.floor_price import FloorPriceProvider
from app.blockchain.providers.opensea_analytics import (
    OpenSeaAnalyticsProvider,
)
from app.schemas.floor_price import CollectionFloorPrice


class OpenSeaFloorPriceProvider(FloorPriceProvider):
    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient | None = None,
    ):
        if not api_key:
            raise ValueError("OpenSea API key is required.")

        self.analytics_provider = OpenSeaAnalyticsProvider(
            api_key=api_key,
            client=client,
        )

    async def get_floor_prices(
        self,
        contract_address: str,
    ) -> list[CollectionFloorPrice]:
        analytics = await self.analytics_provider.get_analytics(
            contract_address=contract_address,
        )

        if analytics is None:
            return []

        return [
            CollectionFloorPrice(
                marketplace="OpenSea",
                floor_price=analytics.floor_price,
                currency=analytics.floor_price_currency,
                collection_url=(
                    f"https://opensea.io/collection/"
                    f"{analytics.collection_slug}"
                ),
                retrieved_at=datetime.now(timezone.utc),
            )
        ]
