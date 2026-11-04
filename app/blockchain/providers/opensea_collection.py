
from typing import Any

import httpx

from app.blockchain.providers.collection import CollectionProvider
from app.schemas.collection import NFTCollection


class OpenSeaCollectionProvider(CollectionProvider):
    BASE_URL = "https://api.opensea.io/api/v2"

    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key
        self.client = client

    @property
    def headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "accept": "application/json",
        }

    async def get_collection(
        self,
        identifier: str,
    ) -> NFTCollection | None:
        should_close_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=15.0)

        try:
            response = await client.get(
                f"{self.BASE_URL}/chain/ethereum/contract/{identifier}",
                headers=self.headers,
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            contract_data: dict[str, Any] = response.json()

            address = contract_data.get("address")

            if not address:
                return None

            slug = contract_data.get("collection")

            collection_data: dict[str, Any] = {}

            if slug:
                collection_response = await client.get(
                    f"{self.BASE_URL}/collections/{slug}",
                    headers=self.headers,
                )

                if collection_response.status_code != 404:
                    collection_response.raise_for_status()
                    collection_data = collection_response.json()

            return self._build_collection(
                contract_data=contract_data,
                collection_data=collection_data,
                fallback_address=str(address),
            )

        finally:
            if should_close_client:
                await client.aclose()

    async def search_collections(
        self,
        query: str,
        limit: int = 10,
    ) -> list[NFTCollection]:
        limit = max(1, min(limit, 50))

        should_close_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=15.0)

        try:
            response = await client.get(
                f"{self.BASE_URL}/search",
                params={
                    "query": query,
                    "asset_types": ["collection"],
                    "limit": limit,
                },
                headers=self.headers,
            )

            response.raise_for_status()

            data: dict[str, Any] = response.json()
            results = data.get("results", [])

            collections: list[NFTCollection] = []

            for result in results:
                collection_data = result.get("collection") or {}

                slug = collection_data.get("collection")

                if not slug:
                    continue

                detail_response = await client.get(
                    f"{self.BASE_URL}/collections/{slug}",
                    headers=self.headers,
                )

                if detail_response.status_code == 404:
                    continue

                detail_response.raise_for_status()

                detail_data: dict[str, Any] = detail_response.json()

                collection = self._build_collection(
                    contract_data={},
                    collection_data=detail_data,
                )

                if collection is not None:
                    collections.append(collection)

            return collections

        finally:
            if should_close_client:
                await client.aclose()

    @staticmethod
    def _build_collection(
        contract_data: dict[str, Any],
        collection_data: dict[str, Any],
        fallback_address: str | None = None,
    ) -> NFTCollection | None:
        contracts = collection_data.get("contracts") or []

        selected_contract = next(
            (
                contract
                for contract in contracts
                if str(contract.get("chain", "")).lower()
                == "ethereum"
            ),
            contracts[0] if contracts else {},
        )

        address = (
            contract_data.get("address")
            or selected_contract.get("address")
            or fallback_address
        )

        if not address:
            return None

        name = (
            collection_data.get("name")
            or contract_data.get("name")
            or "Unknown Collection"
        )

        return NFTCollection(
            contract_address=str(address),
            name=str(name),
            symbol=None,
            description=collection_data.get("description"),
            image_url=collection_data.get("image_url"),
            banner_image_url=collection_data.get(
                "banner_image_url"
            ),
            token_standard=contract_data.get(
                "contract_standard"
            ),
            blockchain=(
                contract_data.get("chain")
                or selected_contract.get("chain")
                or "ethereum"
            ),
        )
