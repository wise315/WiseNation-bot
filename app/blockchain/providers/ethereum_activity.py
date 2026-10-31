
from typing import Any

from web3 import AsyncWeb3

from app.schemas.blockchain_activity import (
    EthereumContractLog,
    EthereumTransaction,
)


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
    def __init__(self, web3: AsyncWeb3):
        self.web3 = web3

    async def get_block_transactions(
        self,
        block_number: int,
    ) -> list[EthereumTransaction]:
        if block_number < 0:
            raise ValueError("Block number cannot be negative.")

        block = await self.web3.eth.get_block(
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
                    transaction_index=int(
                        tx["transactionIndex"]
                    ),
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
        contract_addresses: list[str] | None = None,
        topics: list[Any] | None = None,
    ) -> list[EthereumContractLog]:
        if block_number < 0:
            raise ValueError("Block number cannot be negative.")

        filters: dict[str, Any] = {
            "fromBlock": block_number,
            "toBlock": block_number,
        }

        if contract_addresses:
            filters["address"] = contract_addresses

        if topics is not None:
            filters["topics"] = topics

        logs = await self.web3.eth.get_logs(filters)

        results = []

        for log in logs:
            results.append(
                EthereumContractLog(
                    transaction_hash=_to_hex(
                        log["transactionHash"]
                    ),
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
