from app.blockchain.providers.opensea_sale import OpenSeaSaleProvider
from app.blockchain.providers.sale import SaleProvider
from app.core.config import get_settings


def create_sale_provider() -> SaleProvider:
    settings = get_settings()

    if not settings.opensea_api_key:
        raise RuntimeError(
            "OpenSea API key is not configured."
        )

    return OpenSeaSaleProvider(
        api_key=settings.opensea_api_key,
    )