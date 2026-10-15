import pytest

from app.blockchain.providers.alchemy import AlchemyNFTProvider
from app.blockchain.providers.nft_factory import create_nft_provider
from app.core.config import get_settings


def test_create_nft_provider_with_api_key(monkeypatch):
    settings = get_settings()

    monkeypatch.setattr(
        settings,
        "alchemy_api_key",
        "test-alchemy-key",
    )

    provider = create_nft_provider()

    assert isinstance(provider, AlchemyNFTProvider)
    assert provider.api_key == "test-alchemy-key"


def test_create_nft_provider_without_api_key(monkeypatch):
    settings = get_settings()

    monkeypatch.setattr(
        settings,
        "alchemy_api_key",
        "",
    )

    with pytest.raises(
        RuntimeError,
        match="Alchemy API key is not configured",
    ):
        create_nft_provider()