
import pytest
from eth_abi import encode

from app.events.engine import EventEngine
from app.events.processors.nft_decoder import (
    ERC721_TRANSFER_TOPIC,
    ERC1155_TRANSFER_SINGLE_TOPIC,
    ERC1155_TRANSFER_BATCH_TOPIC,
    NFTEventDecoder,
    ZERO_ADDRESS,
)
from app.events.processors.nft_processor import NFTEventProcessor
from app.events.schemas import EventType
from app.schemas.blockchain_activity import EthereumContractLog


ALICE = "0x" + "11" * 20
BOB = "0x" + "22" * 20
CONTRACT = "0x" + "33" * 20


def address_topic(address: str) -> str:
    return "0x" + address[2:].lower().zfill(64)


def uint_topic(value: int) -> str:
    return "0x" + value.to_bytes(32, "big").hex()


def make_log(
    topics,
    data="0x",
    removed=False,
):
    return EthereumContractLog(
        transaction_hash="0x" + "aa" * 32,
        block_number=100,
        log_index=1,
        contract_address=CONTRACT,
        topics=topics,
        data=data,
        removed=removed,
    )


def test_erc721_transfer():
    decoder = NFTEventDecoder()

    log = make_log([
        ERC721_TRANSFER_TOPIC,
        address_topic(ALICE),
        address_topic(BOB),
        uint_topic(42),
    ])

    events = decoder.decode(log)

    assert len(events) == 1
    assert events[0].event_type == EventType.NFT_TRANSFER
    assert events[0].payload["token_standard"] == "ERC721"
    assert events[0].payload["token_id"] == "42"
    assert events[0].payload["amount"] == 1


def test_erc721_mint():
    decoder = NFTEventDecoder()

    log = make_log([
        ERC721_TRANSFER_TOPIC,
        address_topic(ZERO_ADDRESS),
        address_topic(BOB),
        uint_topic(10),
    ])

    events = decoder.decode(log)

    assert len(events) == 1
    assert events[0].event_type == EventType.NFT_MINT


def test_erc20_transfer_not_misclassified():
    decoder = NFTEventDecoder()

    log = make_log(
        topics=[
            ERC721_TRANSFER_TOPIC,
            address_topic(ALICE),
            address_topic(BOB),
        ],
        data="0x" + encode(
            ["uint256"], [1000]
        ).hex(),
    )

    assert decoder.decode(log) == []


def test_erc1155_single_transfer():
    decoder = NFTEventDecoder()

    log = make_log(
        topics=[
            ERC1155_TRANSFER_SINGLE_TOPIC,
            address_topic(ALICE),
            address_topic(ALICE),
            address_topic(BOB),
        ],
        data="0x" + encode(
            ["uint256", "uint256"],
            [7, 3],
        ).hex(),
    )

    events = decoder.decode(log)

    assert len(events) == 1
    assert events[0].payload["token_id"] == "7"
    assert events[0].payload["amount"] == 3
    assert events[0].event_type == EventType.NFT_TRANSFER


def test_erc1155_single_mint():
    decoder = NFTEventDecoder()

    log = make_log(
        topics=[
            ERC1155_TRANSFER_SINGLE_TOPIC,
            address_topic(ALICE),
            address_topic(ZERO_ADDRESS),
            address_topic(BOB),
        ],
        data="0x" + encode(
            ["uint256", "uint256"],
            [5, 2],
        ).hex(),
    )

    events = decoder.decode(log)

    assert len(events) == 1
    assert events[0].event_type == EventType.NFT_MINT


def test_erc1155_batch_transfer():
    decoder = NFTEventDecoder()

    log = make_log(
        topics=[
            ERC1155_TRANSFER_BATCH_TOPIC,
            address_topic(ALICE),
            address_topic(ALICE),
            address_topic(BOB),
        ],
        data="0x" + encode(
            ["uint256[]", "uint256[]"],
            [[1, 2, 3], [5, 10, 15]],
        ).hex(),
    )

    events = decoder.decode(log)

    assert len(events) == 3
    assert [e.payload["token_id"] for e in events] == [
        "1", "2", "3"
    ]
    assert [e.payload["amount"] for e in events] == [
        5, 10, 15
    ]
    assert [e.payload["batch_index"] for e in events] == [
        0, 1, 2
    ]


def test_unknown_event_ignored():
    decoder = NFTEventDecoder()

    log = make_log([
        "0x" + "ff" * 32,
    ])

    assert decoder.decode(log) == []


def test_removed_log_ignored():
    decoder = NFTEventDecoder()

    log = make_log(
        [
            ERC721_TRANSFER_TOPIC,
            address_topic(ALICE),
            address_topic(BOB),
            uint_topic(1),
        ],
        removed=True,
    )

    assert decoder.decode(log) == []


def test_malformed_event_ignored():
    decoder = NFTEventDecoder()

    log = make_log([
        ERC721_TRANSFER_TOPIC,
        "0x1234",
        address_topic(BOB),
        uint_topic(1),
    ])

    assert decoder.decode(log) == []


def test_erc721_rejects_nonempty_data():
    decoder = NFTEventDecoder()

    log = make_log(
        [
            ERC721_TRANSFER_TOPIC,
            address_topic(ALICE),
            address_topic(BOB),
            uint_topic(1),
        ],
        data="0x1234",
    )

    assert decoder.decode(log) == []


@pytest.mark.asyncio
async def test_processor_publishes_event():
    engine = EventEngine()
    decoder = NFTEventDecoder()
    processor = NFTEventProcessor(decoder, engine)

    received = []

    async def handler(event):
        received.append(event)

    engine.subscribe(EventType.NFT_TRANSFER, handler)

    log = make_log([
        ERC721_TRANSFER_TOPIC,
        address_topic(ALICE),
        address_topic(BOB),
        uint_topic(42),
    ])

    count = await processor.process_log(log)

    assert count == 1
    assert len(received) == 1
    assert received[0].payload["token_id"] == "42"


@pytest.mark.asyncio
async def test_processor_handles_multiple_logs():
    engine = EventEngine()
    decoder = NFTEventDecoder()
    processor = NFTEventProcessor(decoder, engine)

    received = []

    async def handler(event):
        received.append(event)

    engine.subscribe(EventType.NFT_MINT, handler)

    logs = [
        make_log([
            ERC721_TRANSFER_TOPIC,
            address_topic(ZERO_ADDRESS),
            address_topic(BOB),
            uint_topic(1),
        ]),
        make_log([
            ERC721_TRANSFER_TOPIC,
            address_topic(ZERO_ADDRESS),
            address_topic(BOB),
            uint_topic(2),
        ]),
    ]

    count = await processor.process_logs(logs)

    assert count == 2
    assert len(received) == 2


def test_invalid_chain_id():
    with pytest.raises(ValueError):
        NFTEventDecoder(chain_id=0)
