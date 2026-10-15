from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from typing import Any

import httpx

from app.blockchain.providers.sale import SaleProvider
from app.schemas.sale import NFTSale


class OpenSeaSaleProvider(SaleProvider):
    BASE_URL = "https://api.opensea.io/api/v2"

    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key
        self.client = client

    async def get_sales(
        self,
        contract_address: str,
        limit: int = 10,
    ) -> list[NFTSale]:
        limit = max(1, min(limit, 200))

        headers = {
            "x-api-key": self.api_key,
            "accept": "application/json",
        }

        should_close_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=15.0)

        try:
            slug = await self._get_collection_slug(
                client=client,
                contract_address=contract_address,
                headers=headers,
            )

            if slug is None:
                return []

            response = await client.get(
                f"{self.BASE_URL}/events/collection/{slug}",
                params={
                    "event_type": "sale",
                    "limit": limit,
                },
                headers=headers,
            )

            response.raise_for_status()

            data: dict[str, Any] = response.json()
            events = data.get("asset_events", [])

            results: list[NFTSale] = []

            for event in events:
                sale = self._map_sale_event(
                    event=event,
                    fallback_contract_address=contract_address,
                )

                if sale is not None:
                    results.append(sale)

            return results

        finally:
            if should_close_client:
                await client.aclose()

    async def _get_collection_slug(
        self,
        client: httpx.AsyncClient,
        contract_address: str,
        headers: dict[str, str],
    ) -> str | None:
        response = await client.get(
            f"{self.BASE_URL}/chain/ethereum/contract/{contract_address}",
            headers=headers,
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()

        data: dict[str, Any] = response.json()

        slug = data.get("collection")

        if not slug:
            return None

        return str(slug)

    @staticmethod
    def _map_sale_event(
        event: dict[str, Any],
        fallback_contract_address: str,
    ) -> NFTSale | None:
        nft = event.get("nft") or event.get("asset") or {}

        contract_address = (
            nft.get("contract")
            or fallback_contract_address
        )

        token_id = nft.get("identifier")

        if token_id is None:
            return None

        payment = event.get("payment") or {}

        price = OpenSeaSaleProvider._parse_payment_amount(
            payment
        )

        currency = payment.get("symbol")

        buyer = (
            event.get("buyer")
            or event.get("taker")
        )

        seller = (
            event.get("seller")
            or event.get("maker")
        )

        transaction_hash = event.get("transaction")

        timestamp = OpenSeaSaleProvider._parse_timestamp(
            event.get("event_timestamp")
        )

        return NFTSale(
            contract_address=contract_address,
            token_id=str(token_id),
            price=price,
            currency=currency,
            buyer=buyer,
            seller=seller,
            marketplace="OpenSea",
            transaction_hash=transaction_hash,
            timestamp=timestamp,
        )

    @staticmethod
    def _parse_payment_amount(
        payment: dict[str, Any],
    ) -> float | None:
        quantity = payment.get("quantity")

        if quantity is None:
            return None

        decimals = payment.get("decimals", 0)

        try:
            amount = Decimal(str(quantity))
            divisor = Decimal(10) ** int(decimals)
            return float(amount / divisor)
        except (
            InvalidOperation,
            ValueError,
            TypeError,
            OverflowError,
        ):
            return None

    @staticmethod
    def _parse_timestamp(
        timestamp: Any,
    ) -> datetime | None:
        if timestamp is None:
            return None

        try:
            return datetime.fromtimestamp(
                int(timestamp),
                tz=timezone.utc,
            )
        except (
            TypeError,
            ValueError,
            OSError,
            OverflowError,
        ):
            return None