
import pytest

from app.blockchain.providers.nft_factory import create_nft_provider
from app.blockchain.providers.opensea_nft import OpenSeaNFTProvider
from app.core.config import get_settings


def test_create_nft_provider_with_api_key(monkeypatch):
    settings = get_settings()

    monkeypatch.setattr(
        settings,
        "opensea_api_key",
        "test-opensea-key",
    )

    provider = create_nft_provider()

    assert isinstance(provider, OpenSeaNFTProvider)
    assert provider.api_key == "test-opensea-key"


def test_create_nft_provider_without_api_key(monkeypatch):
    settings = get_settings()

    monkeypatch.setattr(
        settings,
        "opensea_api_key",
        "",
    )

    with pytest.raises(
        RuntimeError,
        match="OpenSea API key is not configured",
    ):
        create_nft_provider()
