from datetime import datetime

from pydantic import BaseModel


class NFTSale(BaseModel):
    contract_address: str
    token_id: str
    price: float | None = None
    currency: str | None = None
    buyer: str | None = None
    seller: str | None = None
    marketplace: str | None = None
    transaction_hash: str | None = None
    timestamp: datetime | None = None