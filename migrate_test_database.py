
import asyncio
import os
import subprocess
import sys

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine


load_dotenv()


async def verify_database(database_url: str) -> None:
    engine = create_async_engine(database_url)

    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT current_database(), current_user"
                )
            )

            database_name, username = result.one()

            if database_name != "nft_bot_test":
                raise RuntimeError(
                    f"Unsafe database target: {database_name}"
                )

            print(f"Verified database: {database_name}")
            print(f"Connected as: {username}")

    finally:
        await engine.dispose()


def main() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "TEST_DATABASE_URL is missing from .env"
        )

    parsed = make_url(database_url)

    if parsed.database != "nft_bot_test":
        raise RuntimeError(
            "TEST_DATABASE_URL must target nft_bot_test."
        )

    asyncio.run(verify_database(database_url))

    environment = os.environ.copy()
    environment["ALEMBIC_DATABASE_URL"] = database_url

    print("Applying Alembic migrations to nft_bot_test...")

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=environment,
        check=True,
    )

    print("Verifying migration revision...")

    subprocess.run(
        [sys.executable, "-m", "alembic", "current"],
        env=environment,
        check=True,
    )


if __name__ == "__main__":
    main()
