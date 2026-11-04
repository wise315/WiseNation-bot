
import pytest

from app.blockchain.providers.collection_factory import (
    create_collection_provider,
)
from app.blockchain.providers.opensea_collection import (
    OpenSeaCollectionProvider,
)
from app.core.config import get_settings


def test_create_collection_provider_with_api_key(monkeypatch):
    settings = get_settings()

    monkeypatch.setattr(
        settings,
        "opensea_api_key",
        "test-opensea-key",
    )

    provider = create_collection_provider()

    assert isinstance(provider, OpenSeaCollectionProvider)
    assert provider.api_key == "test-opensea-key"


def test_create_collection_provider_without_api_key(monkeypatch):
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
        create_collection_provider()
