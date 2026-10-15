from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class WalletTransaction(BaseModel):
    hash: str
    wallet_address: str
    from_address: str
    to_address: str | None = None
    value: Decimal
    block_number: int
    timestamp: datetime | None = None
    status: str