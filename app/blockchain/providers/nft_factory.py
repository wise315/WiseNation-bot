from app.blockchain.providers.alchemy import AlchemyNFTProvider
from app.blockchain.providers.nft import NFTProvider
from app.core.config import get_settings


def create_nft_provider() -> NFTProvider:
    settings = get_settings()

    if not settings.alchemy_api_key:
        raise RuntimeError(
            "Alchemy API key is not configured."
        )

    return AlchemyNFTProvider(
        api_key=settings.alchemy_api_key,
    )