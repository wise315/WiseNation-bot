from app.core.config import get_settings


def main() -> None:
    settings = get_settings()

    print("=" * 50)
    print(settings.app_name)
    print("=" * 50)
    print(f"Environment: {settings.app_env}")
    print(f"Debug: {settings.debug}")
    print(f"Database: {settings.postgres_db}")
    print(f"Ethereum Chain ID: {settings.ethereum_chain_id}")


if __name__ == "__main__":
    main()