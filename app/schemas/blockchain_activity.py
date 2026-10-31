
from pydantic import BaseModel, Field


class EthereumTransaction(BaseModel):
    transaction_hash: str
    block_number: int = Field(ge=0)
    transaction_index: int = Field(ge=0)
    from_address: str
    to_address: str | None = None
    value_wei: int = Field(ge=0)
    input_data: str = "0x"


class EthereumContractLog(BaseModel):
    transaction_hash: str
    block_number: int = Field(ge=0)
    log_index: int = Field(ge=0)
    contract_address: str
    topics: list[str] = Field(default_factory=list)
    data: str = "0x"
    removed: bool = False
