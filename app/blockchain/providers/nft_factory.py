
from app.blockchain.providers.nft import NFTProvider
from app.blockchain.providers.opensea_nft import OpenSeaNFTProvider
from app.core.config import get_settings


def create_nft_provider() -> NFTProvider:
    settings = get_settings()

    if not settings.opensea_api_key:
        raise RuntimeError("OpenSea API key is not configured.")

    return OpenSeaNFTProvider(
        api_key=settings.opensea_api_key,
    )
