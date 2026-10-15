from pydantic import BaseModel


class CollectionAnalytics(BaseModel):
    contract_address: str
    collection_slug: str

    floor_price: float | None = None
    floor_price_currency: str | None = None

    one_day_volume: float | None = None
    one_day_volume_currency: str | None = None
    one_day_sales: int | None = None

    seven_day_volume: float | None = None
    seven_day_volume_currency: str | None = None
    seven_day_sales: int | None = None

    thirty_day_volume: float | None = None
    thirty_day_volume_currency: str | None = None
    thirty_day_sales: int | None = None

    total_volume: float | None = None
    total_volume_currency: str | None = None
    total_sales: int | None = None

    num_owners: int | None = None
    total_supply: int | None = None
    unique_item_count: int | None = None