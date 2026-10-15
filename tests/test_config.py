from app.core.config import get_settings


def test_ethereum_configuration_exists():
    settings = get_settings()

    assert settings.ethereum_rpc_http
    assert settings.ethereum_chain_id == 1