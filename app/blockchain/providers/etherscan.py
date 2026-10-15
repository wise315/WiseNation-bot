from datetime import datetime, timezone
from decimal import Decimal

import httpx

from app.blockchain.providers.transaction import TransactionHistoryProvider
from app.schemas.transaction import WalletTransaction


class EtherscanTransactionProvider(TransactionHistoryProvider):
    BASE_URL = "https://api.etherscan.io/v2/api"

    def __init__(
        self,
        api_key: str,
        chain_id: int = 1,
        client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key
        self.chain_id = chain_id
        self.client = client

    async def get_transactions(
        self,
        address: str,
        limit: int = 10,
    ) -> list[WalletTransaction]:
        if limit < 1:
            return []

        params = {
            "chainid": self.chain_id,
            "module": "account",
            "action": "txlist",
            "address": address,
            "page": 1,
            "offset": limit,
            "sort": "desc",
            "apikey": self.api_key,
        }

        should_close_client = self.client is None

        client = self.client or httpx.AsyncClient(
            timeout=15.0,
        )

        try:
            response = await client.get(
                self.BASE_URL,
                params=params,
            )

            response.raise_for_status()

            data = response.json()

            if data.get("status") == "0":
                return []

            transactions = []

            for item in data.get("result", []):
                timestamp = item.get("timeStamp")

                parsed_timestamp = None

                if timestamp:
                    parsed_timestamp = datetime.fromtimestamp(
                        int(timestamp),
                        tz=timezone.utc,
                    )

                transactions.append(
                    WalletTransaction(
                        hash=item["hash"],
                        wallet_address=address,
                        from_address=item["from"],
                        to_address=item.get("to") or None,
                        value=(
                            Decimal(item["value"])
                            / Decimal("1000000000000000000")
                        ),
                        block_number=int(item["blockNumber"]),
                        timestamp=parsed_timestamp,
                        status=(
                            "failed"
                            if item.get("isError") == "1"
                            else "success"
                        ),
                    )
                )

            return transactions

        finally:
            if should_close_client:
                await client.aclose()