
from app.blockchain.providers.collection import CollectionProvider
from app.blockchain.providers.opensea_collection import (
    OpenSeaCollectionProvider,
)
from app.core.config import get_settings


def create_collection_provider() -> CollectionProvider:
    settings = get_settings()

    if not settings.opensea_api_key:
        raise RuntimeError(
            "OpenSea API key is not configured."
        )

    return OpenSeaCollectionProvider(
        api_key=settings.opensea_api_key,
    )
