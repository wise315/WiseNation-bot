
from typing import Any

from eth_abi import decode
from eth_utils import keccak

from app.events.schemas import BlockchainEvent, EventType
from app.schemas.blockchain_activity import EthereumContractLog


ZERO_ADDRESS = "0x" + "0" * 40

ERC721_TRANSFER_TOPIC = "0x" + keccak(
    text="Transfer(address,address,uint256)"
).hex()

ERC1155_TRANSFER_SINGLE_TOPIC = "0x" + keccak(
    text="TransferSingle(address,address,address,uint256,uint256)"
).hex()

ERC1155_TRANSFER_BATCH_TOPIC = "0x" + keccak(
    text="TransferBatch(address,address,address,uint256[],uint256[])"
).hex()


def _decode_address(topic: str) -> str:
    raw = bytes.fromhex(topic.removeprefix("0x"))

    if len(raw) != 32:
        raise ValueError("Invalid address topic length.")

    if any(raw[:12]):
        raise ValueError("Invalid address topic padding.")

    return "0x" + raw[-20:].hex()


def _decode_uint(topic: str) -> int:
    raw = bytes.fromhex(topic.removeprefix("0x"))

    if len(raw) != 32:
        raise ValueError("Invalid uint256 topic length.")

    return int.from_bytes(raw, byteorder="big")


def _decode_data(data: str, types: list[str]) -> tuple[Any, ...]:
    raw = bytes.fromhex(data.removeprefix("0x"))
    return decode(types, raw)


class NFTEventDecoder:
    def __init__(self, chain_id: int = 1):
        if chain_id <= 0:
            raise ValueError("chain_id must be positive.")

        self.chain_id = chain_id

    def decode(
        self,
        log: EthereumContractLog,
    ) -> list[BlockchainEvent]:
        if log.removed or not log.topics:
            return []

        signature = log.topics[0].lower()

        try:
            if signature == ERC721_TRANSFER_TOPIC:
                return self._decode_erc721(log)

            if signature == ERC1155_TRANSFER_SINGLE_TOPIC:
                return self._decode_erc1155_single(log)

            if signature == ERC1155_TRANSFER_BATCH_TOPIC:
                return self._decode_erc1155_batch(log)

        except (ValueError, TypeError, OverflowError):
            return []

        return []

    def _create_event(
        self,
        log: EthereumContractLog,
        token_standard: str,
        from_address: str,
        to_address: str,
        token_id: int,
        amount: int,
        batch_index: int | None = None,
    ) -> BlockchainEvent:
        is_mint = from_address.lower() == ZERO_ADDRESS

        payload: dict[str, Any] = {
            "contract_address": log.contract_address,
            "transaction_hash": log.transaction_hash,
            "block_number": log.block_number,
            "log_index": log.log_index,
            "token_standard": token_standard,
            "from_address": from_address,
            "to_address": to_address,
            "token_id": str(token_id),
            "amount": amount,
        }

        if batch_index is not None:
            payload["batch_index"] = batch_index

        return BlockchainEvent(
            event_type=(
                EventType.NFT_MINT
                if is_mint
                else EventType.NFT_TRANSFER
            ),
            source="ethereum_contract_log",
            chain_id=self.chain_id,
            payload=payload,
        )

    def _decode_erc721(
        self,
        log: EthereumContractLog,
    ) -> list[BlockchainEvent]:
        # ERC-721 has four topics and empty event data.
        # Standard ERC-20 transfers normally have three topics.
        if len(log.topics) != 4:
            return []

        if bytes.fromhex(log.data.removeprefix("0x")):
            return []

        from_address = _decode_address(log.topics[1])
        to_address = _decode_address(log.topics[2])
        token_id = _decode_uint(log.topics[3])

        return [
            self._create_event(
                log=log,
                token_standard="ERC721",
                from_address=from_address,
                to_address=to_address,
                token_id=token_id,
                amount=1,
            )
        ]

    def _decode_erc1155_single(
        self,
        log: EthereumContractLog,
    ) -> list[BlockchainEvent]:
        if len(log.topics) != 4:
            return []

        from_address = _decode_address(log.topics[2])
        to_address = _decode_address(log.topics[3])

        token_id, amount = _decode_data(
            log.data,
            ["uint256", "uint256"],
        )

        return [
            self._create_event(
                log=log,
                token_standard="ERC1155",
                from_address=from_address,
                to_address=to_address,
                token_id=token_id,
                amount=amount,
            )
        ]

    def _decode_erc1155_batch(
        self,
        log: EthereumContractLog,
    ) -> list[BlockchainEvent]:
        if len(log.topics) != 4:
            return []

        from_address = _decode_address(log.topics[2])
        to_address = _decode_address(log.topics[3])

        token_ids, amounts = _decode_data(
            log.data,
            ["uint256[]", "uint256[]"],
        )

        if len(token_ids) != len(amounts):
            return []

        return [
            self._create_event(
                log=log,
                token_standard="ERC1155",
                from_address=from_address,
                to_address=to_address,
                token_id=token_id,
                amount=amount,
                batch_index=index,
            )
            for index, (token_id, amount) in enumerate(
                zip(token_ids, amounts)
            )
        ]
