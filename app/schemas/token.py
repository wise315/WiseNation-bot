from decimal import Decimal

from pydantic import BaseModel


class TokenBalance(BaseModel):
    symbol: str
    address: str
    balance: Decimal