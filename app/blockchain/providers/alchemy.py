from typing import Any

import httpx

from app.blockchain.providers.nft import NFTProvider
from app.schemas.nft import WalletNFT


class AlchemyNFTProvider(NFTProvider):
    BASE_URL = "https://eth-mainnet.g.alchemy.com/nft/v3"

    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key
        self.client = client

    async def get_nfts(
        self,
        address: str,
        limit: int = 20,
    ) -> list[WalletNFT]:
        if limit < 1:
            return []

        url = (
            f"{self.BASE_URL}/"
            f"{self.api_key}/getNFTsForOwner"
        )

        params = {
            "owner": address,
            "pageSize": limit,
            "withMetadata": "true",
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

            nfts: list[WalletNFT] = []

            for item in data.get("ownedNfts", []):
                contract = item.get("contract", {})

                collection = item.get("collection", {})
                open_sea_metadata = contract.get(
                    "openSeaMetadata",
                    {},
                )

                collection_name = (
                    collection.get("name")
                    or open_sea_metadata.get("collectionName")
                    or contract.get("name")
                )

                image_data = item.get("image", {})

                image_url = (
                    image_data.get("cachedUrl")
                    or image_data.get("originalUrl")
                )

                if image_url is None:
                    raw_metadata = (
                        item.get("raw", {}).get("metadata", {})
                    )
                    image_url = raw_metadata.get("image")

                nfts.append(
                    WalletNFT(
                        contract_address=contract["address"],
                        token_id=str(item["tokenId"]),
                        collection_name=collection_name,
                        name=item.get("name"),
                        image_url=image_url,
                        token_standard=item.get(
                            "tokenType",
                            contract.get("tokenType", "UNKNOWN"),
                        ),
                        wallet_address=address,
                    )
                )

            return nfts

        finally:
            if should_close_client:
                await client.aclose()