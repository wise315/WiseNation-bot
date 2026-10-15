from app.blockchain.providers.collection import CollectionProvider
from app.blockchain.providers.floor_price import FloorPriceProvider
from app.blockchain.providers.analytics import (
    CollectionAnalyticsProvider,
)
from app.schemas.collection_analytics import CollectionAnalytics
from app.blockchain.providers.sale import SaleProvider
from app.schemas.sale import NFTSale
from app.schemas.collection import NFTCollection
from app.schemas.floor_price import CollectionFloorPrice


class CollectionService:
    def __init__(
        self,
        collection_provider: CollectionProvider,
        floor_price_provider: FloorPriceProvider | None = None,
        sale_provider: SaleProvider | None = None,
        analytics_provider: CollectionAnalyticsProvider | None = None,
    ):
        self.collection_provider = collection_provider
        self.floor_price_provider = floor_price_provider
        self.sale_provider = sale_provider
        self.analytics_provider = analytics_provider

    async def get_collection(
        self,
        identifier: str,
    ) -> NFTCollection | None:
        return await self.collection_provider.get_collection(
            identifier=identifier,
        )

    async def search_collections(
        self,
        query: str,
        limit: int = 10,
    ) -> list[NFTCollection]:
        return await self.collection_provider.search_collections(
            query=query,
            limit=limit,
        )
        
    async def get_floor_prices(
        self,
        contract_address: str,
    ) -> list[CollectionFloorPrice]:
        if self.floor_price_provider is None:
            raise RuntimeError(
                "Floor price provider is not configured."
            )
            
        return await self.floor_price_provider.get_floor_prices(
            contract_address=contract_address
        )
        
    async def get_sales(
        self,
        contract_address: str,
        limit: int = 10,
    ) -> list[NFTSale]:
        if self.sale_provider is None:
            raise RuntimeError(
                "Sale provider is not configured."
            )
            
        return await self.sale_provider.get_sales(
            contract_address=contract_address,
            limit=limit,
        )
        
    async def get_analytics(
        self,
        contract_address: str,
    ) -> CollectionAnalytics | None:
        if self.analytics_provider is None:
            raise RuntimeError(
                "Collection analytics provider is not configured."
            )
            
        return await self.analytics_provider.get_analytics(
            contract_address=contract_address
        )