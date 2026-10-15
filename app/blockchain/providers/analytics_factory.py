from app.blockchain.providers.analytics import CollectionAnalyticsProvider
from app.blockchain.providers.opensea_analytics import (
    OpenSeaAnalyticsProvider,
)
from app.core.config import get_settings


def create_collection_analytics_provider() -> CollectionAnalyticsProvider:
    settings = get_settings()

    if not settings.opensea_api_key:
        raise RuntimeError(
            "OpenSea API key is not configured."
        )

    return OpenSeaAnalyticsProvider(
        api_key=settings.opensea_api_key,
    )