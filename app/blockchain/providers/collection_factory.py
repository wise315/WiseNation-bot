from app.blockchain.providers.alchemy_collection import (
    AlchemyCollectionProvider,
)
from app.blockchain.providers.collection import CollectionProvider
from app.core.config import get_settings


def create_collection_provider() -> CollectionProvider:
    settings = get_settings()

    if not settings.alchemy_api_key:
        raise RuntimeError(
            "Alchemy API key is not configured."
        )

    return AlchemyCollectionProvider(
        api_key=settings.alchemy_api_key,
    )