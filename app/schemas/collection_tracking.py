from datetime import datetime

from pydantic import BaseModel


class CollectionTracking(BaseModel):
    id: int
    user_id: int
    contract_address: str
    collection_name: str | None = None
    blockchain: str = "ethereum"
    is_active: bool = True
    created_at: datetime