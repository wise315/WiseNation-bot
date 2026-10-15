from abc import ABC, abstractmethod

from app.schemas.floor_price import CollectionFloorPrice


class FloorPriceProvider(ABC):
    @abstractmethod
    async def get_floor_prices(
        self,
        contract_address: str,
    ) -> list[CollectionFloorPrice]:
        raise NotImplementedError