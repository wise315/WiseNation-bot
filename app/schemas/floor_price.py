from datetime import datetime

from pydantic import BaseModel


class CollectionFloorPrice(BaseModel):
    marketplace: str
    floor_price: float | None = None
    currency: str | None = None
    collection_url: str | None = None
    retrieved_at: datetime | None = None
    error: str | None = None