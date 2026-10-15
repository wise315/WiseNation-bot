from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NFT Telegram Bot"
    app_env: str = "development"
    debug: bool = True

    telegram_bot_token: str = ""

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "nft_bot"
    postgres_user: str = "postgres"
    postgres_password: str = ""

    database_url: str = ""

    ethereum_rpc_http: str = ""
    ethereum_rpc_ws: str = ""
    ethereum_chain_id: int = 1

    ethereum_rpc_http_backup: str = ""
    ethereum_rpc_ws_backup: str = ""

    etherscan_api_key: str = ""
    alchemy_api_key: str = ""
    opensea_api_key: str = ""

    encryption_key: str = ""

    max_transaction_eth: float = 1
    max_daily_spend_eth: float = 5

    transaction_confirmations: int = 1

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()