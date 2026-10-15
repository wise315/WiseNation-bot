from typing import Any

import httpx

from app.blockchain.providers.collection import CollectionProvider
from app.schemas.collection import NFTCollection


class AlchemyCollectionProvider(CollectionProvider):
    BASE_URL = "https://eth-mainnet.g.alchemy.com/nft/v3"

    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key
        self.client = client

    async def get_collection(
        self,
        identifier: str,
    ) -> NFTCollection | None:
        url = (
            f"{self.BASE_URL}/"
            f"{self.api_key}/getContractMetadata"
        )

        params = {
            "contractAddress": identifier,
        }

        should_close_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=15.0)

        try:
            response = await client.get(
                url,
                params=params,
            )
            response.raise_for_status()

            data: dict[str, Any] = response.json()

            if not data.get("address"):
                return None

            opensea_metadata = data.get(
                "openseaMetadata",
                {},
            )

            return NFTCollection(
                contract_address=data["address"],
                name=(
                    data.get("name")
                    or opensea_metadata.get("collectionName")
                    or "Unknown Collection"
                ),
                symbol=data.get("symbol"),
                description=opensea_metadata.get("description"),
                image_url=opensea_metadata.get("imageUrl"),
                banner_image_url=opensea_metadata.get(
                    "bannerImageUrl"
                ),
                token_standard=data.get("tokenType"),
                blockchain="ethereum",
            )

        finally:
            if should_close_client:
                await client.aclose()

    async def search_collections(
        self,
        query: str,
        limit: int = 10,
    ) -> list[NFTCollection]:
        raise NotImplementedError(
            "Alchemy does not provide text-based collection search "
            "through the current NFT V3 API."
        )