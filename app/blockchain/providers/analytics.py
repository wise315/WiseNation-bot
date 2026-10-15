from abc import ABC, abstractmethod

from app.schemas.collection_analytics import CollectionAnalytics


class CollectionAnalyticsProvider(ABC):
    @abstractmethod
    async def get_analytics(
        self,
        contract_address: str,
    ) -> CollectionAnalytics | None:
        raise NotImplementedError