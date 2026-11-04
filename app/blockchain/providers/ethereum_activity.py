from typing import Any

from app.schemas.blockchain_activity import (
    EthereumContractLog,
    EthereumTransaction,
)
from app.blockchain.providers.ethereum import EthereumProvider


def _to_hex(value: Any) -> str:
    if isinstance(value, str):
        return value

    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()

    if hasattr(value, "hex"):
        result = value.hex()
        return result if result.startswith("0x") else "0x" + result

    raise TypeError("Expected a hexadecimal value.")


class EthereumActivityProvider:
    def __init__(self, provider: Any):
        self.provider = provider

    async def _get_block(
        self,
        block_number: int,
        full_transactions: bool = False,
    ) -> Any:
        if isinstance(self.provider, EthereumProvider):
            return await self.provider.get_block(
                block_number,
                full_transactions=full_transactions,
            )

        return await self.provider.eth.get_block(
            block_number,
            full_transactions=full_transactions,
        )

    async def _get_logs(
        self,
        filters: dict,
    ) -> list:
        if isinstance(self.provider, EthereumProvider):
            return await self.provider.get_logs(filters)

        return await self.provider.eth.get_logs(filters)

    async def get_block_metadata(
        self,
        block_number: int,
    ) -> tuple[str, str]:
        if (
            not isinstance(block_number, int)
            or isinstance(block_number, bool)
            or block_number < 0
        ):
            raise ValueError("Invalid block number.")

        block = await self._get_block(block_number)

        block_hash = _to_hex(block["hash"]).lower()
        parent_hash = _to_hex(block["parentHash"]).lower()

        for value in (block_hash, parent_hash):
            if len(value) != 66:
                raise ValueError("Ethereum returned an invalid block hash.")

            try:
                bytes.fromhex(value[2:])
            except ValueError as exc:
                raise ValueError(
                    "Ethereum returned an invalid block hash."
                ) from exc

        return block_hash, parent_hash

    async def get_block_transactions(
        self,
        block_number: int,
    ) -> list[EthereumTransaction]:
        if block_number < 0:
            raise ValueError("Block number cannot be negative.")

        block = await self._get_block(
            block_number,
            full_transactions=True,
        )

        transactions = block.get("transactions", [])
        results = []

        for tx in transactions:
            results.append(
                EthereumTransaction(
                    transaction_hash=_to_hex(tx["hash"]),
                    block_number=int(tx["blockNumber"]),
                    transaction_index=int(tx["transactionIndex"]),
                    from_address=tx["from"],
                    to_address=tx.get("to"),
                    value_wei=int(tx["value"]),
                    input_data=_to_hex(tx.get("input", "0x")),
                )
            )

        return results

    async def get_block_logs(
        self,
        block_number: int,
        contract_addresses=None,
        topics=None,
    ) -> list[EthereumContractLog]:
        if block_number < 0:
            raise ValueError("Block number cannot be negative.")

        filters = {
            "fromBlock": block_number,
            "toBlock": block_number,
        }

        if contract_addresses:
            filters["address"] = contract_addresses

        if topics is not None:
            filters["topics"] = topics

        logs = await self._get_logs(filters)

        results = []

        for log in logs:
            results.append(
                EthereumContractLog(
                    transaction_hash=_to_hex(log["transactionHash"]),
                    block_number=int(log["blockNumber"]),
                    log_index=int(log["logIndex"]),
                    contract_address=log["address"],
                    topics=[
                        _to_hex(topic)
                        for topic in log["topics"]
                    ],
                    data=_to_hex(log.get("data", "0x")),
                    removed=bool(log.get("removed", False)),
                )
            )

        return results