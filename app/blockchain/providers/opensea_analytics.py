from typing import Any

import httpx

from app.blockchain.providers.analytics import CollectionAnalyticsProvider
from app.schemas.collection_analytics import CollectionAnalytics


class OpenSeaAnalyticsProvider(CollectionAnalyticsProvider):
    BASE_URL = "https://api.opensea.io/api/v2"

    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key
        self.client = client

    async def get_analytics(
        self,
        contract_address: str,
    ) -> CollectionAnalytics | None:
        headers = {
            "x-api-key": self.api_key,
            "accept": "application/json",
        }

        should_close_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=15.0)

        try:
            collection = await self._get_collection(
                client=client,
                contract_address=contract_address,
                headers=headers,
            )

            if collection is None:
                return None

            slug = collection.get("collection")

            if not slug:
                return None

            stats = await self._get_collection_stats(
                client=client,
                slug=str(slug),
                headers=headers,
            )

            if stats is None:
                return None

            return self._build_analytics(
                contract_address=contract_address,
                collection=collection,
                stats=stats,
                slug=str(slug),
            )

        finally:
            if should_close_client:
                await client.aclose()

    async def _get_collection(
        self,
        client: httpx.AsyncClient,
        contract_address: str,
        headers: dict[str, str],
    ) -> dict[str, Any] | None:
        response = await client.get(
            f"{self.BASE_URL}/chain/ethereum/contract/{contract_address}",
            headers=headers,
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()

        data: dict[str, Any] = response.json()

        collection = data.get("collection")

        if not collection:
            return None

        return data

    async def _get_collection_stats(
        self,
        client: httpx.AsyncClient,
        slug: str,
        headers: dict[str, str],
    ) -> dict[str, Any] | None:
        response = await client.get(
            f"{self.BASE_URL}/collections/{slug}/stats",
            headers=headers,
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()

        data: dict[str, Any] = response.json()

        if not data:
            return None

        return data

    @classmethod
    def _build_analytics(
        cls,
        contract_address: str,
        collection: dict[str, Any],
        stats: dict[str, Any],
        slug: str,
    ) -> CollectionAnalytics:
        intervals = stats.get("intervals", [])
        total = stats.get("total") or {}

        interval_map: dict[str, dict[str, Any]] = {
            str(interval.get("interval")): interval
            for interval in intervals
            if interval.get("interval")
        }

        one_day = interval_map.get("one_day", {})
        seven_days = interval_map.get("seven_days", {})
        thirty_days = interval_map.get("thirty_days", {})

        return CollectionAnalytics(
            contract_address=contract_address,
            collection_slug=slug,
            floor_price=cls._to_float(
                total.get("floor_price")
            ),
            floor_price_currency=total.get(
                "floor_price_symbol"
            ),
            one_day_volume=cls._to_float(
                one_day.get("volume")
            ),
            one_day_volume_currency=one_day.get(
                "volume_symbol"
            ),
            one_day_sales=cls._to_int(
                one_day.get("sales")
            ),
            seven_day_volume=cls._to_float(
                seven_days.get("volume")
            ),
            seven_day_volume_currency=seven_days.get(
                "volume_symbol"
            ),
            seven_day_sales=cls._to_int(
                seven_days.get("sales")
            ),
            thirty_day_volume=cls._to_float(
                thirty_days.get("volume")
            ),
            thirty_day_volume_currency=thirty_days.get(
                "volume_symbol"
            ),
            thirty_day_sales=cls._to_int(
                thirty_days.get("sales")
            ),
            total_volume=cls._to_float(
                total.get("volume")
            ),
            total_volume_currency=total.get(
                "volume_symbol"
            ),
            total_sales=cls._to_int(
                total.get("sales")
            ),
            num_owners=cls._to_int(
                total.get("num_owners")
            ),
            total_supply=cls._to_int(
                collection.get("total_supply")
            ),
            unique_item_count=cls._to_int(
                collection.get("unique_item_count")
            ),
        )

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_int(value: Any) -> int | None:
        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None