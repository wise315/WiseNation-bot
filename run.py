import asyncio

from app.bot.bot import create_bot, create_dispatcher
from app.core.config import get_settings


async def main() -> None:
    settings = get_settings()

    if not settings.telegram_bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not configured in the .env file."
        )

    bot = create_bot(settings.telegram_bot_token)
    dispatcher = create_dispatcher()

    print("=" * 50)
    print("🐱‍🏍WiseNation Bot")
    print("=" * 50)
    print(f"Environment: {settings.app_env}")
    print("Telegram bot starting...")

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())