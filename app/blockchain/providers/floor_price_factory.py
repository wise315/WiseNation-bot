
from app.blockchain.providers.floor_price import FloorPriceProvider
from app.blockchain.providers.opensea_floor_price import (
    OpenSeaFloorPriceProvider,
)
from app.core.config import get_settings


def create_floor_price_provider() -> FloorPriceProvider:
    settings = get_settings()

    if not settings.opensea_api_key:
        raise RuntimeError("OpenSea API key is not configured.")

    return OpenSeaFloorPriceProvider(
        api_key=settings.opensea_api_key,
    )
