from pydantic import BaseModel


class WalletNFT(BaseModel):
    contract_address: str
    token_id: str
    collection_name: str | None = None
    name: str | None = None
    image_url: str | None = None
    token_standard: str
    wallet_address: str