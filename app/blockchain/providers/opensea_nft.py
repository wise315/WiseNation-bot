
from typing import Any

import httpx

from app.blockchain.providers.nft import NFTProvider
from app.schemas.nft import WalletNFT


class OpenSeaNFTProvider(NFTProvider):
    BASE_URL = "https://api.opensea.io/api/v2"
    MAX_PAGE_SIZE = 200

    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient | None = None,
    ):
        if not api_key:
            raise ValueError("OpenSea API key is required.")

        self.api_key = api_key
        self.client = client

    async def get_nfts(
        self,
        address: str,
        limit: int = 20,
    ) -> list[WalletNFT]:
        if limit < 1:
            raise ValueError("NFT limit must be at least 1.")

        owns_client = self.client is None

        client = self.client or httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "x-api-key": self.api_key,
                "accept": "application/json",
            },
            timeout=20.0,
        )

        try:
            results: list[WalletNFT] = []
            next_cursor: str | None = None

            while len(results) < limit:
                page_limit = min(
                    limit - len(results),
                    self.MAX_PAGE_SIZE,
                )

                params: dict[str, Any] = {
                    "limit": page_limit,
                }

                if next_cursor:
                    params["next"] = next_cursor

                response = await client.get(
                    f"/chain/ethereum/account/{address}/nfts",
                    params=params,
                )
                response.raise_for_status()

                data = response.json()

                for item in data.get("nfts", []):
                    nft = self._build_wallet_nft(
                        item,
                        address,
                    )

                    if nft is not None:
                        results.append(nft)

                    if len(results) >= limit:
                        break

                next_cursor = data.get("next")

                if not next_cursor:
                    break

            return results

        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    def _build_wallet_nft(
        item: dict[str, Any],
        wallet_address: str,
    ) -> WalletNFT | None:
        contract_address = item.get("contract")
        token_id = item.get("identifier")

        if not contract_address or token_id is None:
            return None

        return WalletNFT(
            contract_address=contract_address,
            token_id=str(token_id),
            collection_name=item.get("collection"),
            name=item.get("name"),
            image_url=(
                item.get("image_url")
                or item.get("display_image_url")
                or item.get("original_image_url")
            ),
            token_standard=(
                item.get("token_standard") or "ERC721"
            ).upper(),
            wallet_address=wallet_address,
        )
