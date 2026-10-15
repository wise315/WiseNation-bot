from abc import ABC, abstractmethod

from app.schemas.sale import NFTSale


class SaleProvider(ABC):
    @abstractmethod
    async def get_sales(
        self,
        contract_address: str,
        limit: int = 10,
    ) -> list[NFTSale]:
        raise NotImplementedError