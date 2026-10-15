import pytest

from app.blockchain.providers.etherscan import (
    EtherscanTransactionProvider,
)
from app.blockchain.providers.factory import (
    create_transaction_history_provider,
)
from app.core.config import get_settings


def test_transaction_provider_factory(monkeypatch):
    get_settings.cache_clear()

    monkeypatch.setenv(
        "ETHERSCAN_API_KEY",
        "test-api-key",
    )

    provider = create_transaction_history_provider()

    assert isinstance(
        provider,
        EtherscanTransactionProvider,
    )

    assert provider.api_key == "test-api-key"
    assert provider.chain_id == 1

    get_settings.cache_clear()


def test_transaction_provider_factory_requires_api_key(monkeypatch):
    get_settings.cache_clear()

    monkeypatch.setenv(
        "ETHERSCAN_API_KEY",
        "",
    )

    with pytest.raises(
        RuntimeError,
        match="Etherscan API key is not configured.",
    ):
        create_transaction_history_provider()

    get_settings.cache_clear()