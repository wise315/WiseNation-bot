import pytest

from app.blockchain.providers.alchemy_collection import (
    AlchemyCollectionProvider,
)
from app.blockchain.providers.collection_factory import (
    create_collection_provider,
)
from app.core.config import get_settings


def test_create_collection_provider_with_api_key(monkeypatch):
    settings = get_settings()

    monkeypatch.setattr(
        settings,
        "alchemy_api_key",
        "test-alchemy-key",
    )

    provider = create_collection_provider()

    assert isinstance(
        provider,
        AlchemyCollectionProvider,
    )

    assert provider.api_key == "test-alchemy-key"


def test_create_collection_provider_without_api_key(monkeypatch):
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
        create_collection_provider()