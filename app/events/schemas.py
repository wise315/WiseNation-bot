
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    BLOCK_MINED = "block.mined"
    NFT_SALE = "nft.sale"
    NFT_TRANSFER = "nft.transfer"
    NFT_MINT = "nft.mint"
    FLOOR_PRICE_CHANGED = "collection.floor_changed"
    WALLET_TRANSACTION = "wallet.transaction"
    WALLET_ACTIVITY = "wallet.activity"


class BlockchainEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: EventType
    source: str
    chain_id: int = Field(gt=0)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    payload: dict[str, Any] = Field(default_factory=dict)
