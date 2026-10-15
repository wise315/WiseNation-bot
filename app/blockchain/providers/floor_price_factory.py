from app.blockchain.providers.alchemy_floor_price import (
    AlchemyFloorPriceProvider,
)
from app.blockchain.providers.floor_price import FloorPriceProvider
from app.core.config import get_settings


def create_floor_price_provider() -> FloorPriceProvider:
    settings = get_settings()

    if not settings.alchemy_api_key:
        raise RuntimeError("Alchemy API key is not configured.")

    return AlchemyFloorPriceProvider(
        api_key=settings.alchemy_api_key,
    )