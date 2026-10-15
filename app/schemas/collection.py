from pydantic import BaseModel


class NFTCollection(BaseModel):
    contract_address: str
    name: str
    symbol: str | None = None
    description: str | None = None
    image_url: str | None = None
    banner_image_url: str | None = None
    token_standard: str | None = None
    blockchain: str