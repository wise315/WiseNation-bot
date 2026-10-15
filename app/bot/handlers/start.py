from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.main_menu import main_menu_keyboard
from app.database.session import AsyncSessionLocal
from app.services.user_service import UserService


router = Router()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    user = message.from_user

    if user is None:
        return

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        db_user, created = await user_service.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )

    first_name = user.first_name or "there"

    if created:
        welcome_text = (
            f"👋 Welcome, {first_name}!\n\n"
            "Your account has been created successfully."
        )
    else:
        welcome_text = (
            f"👋 Welcome back, {first_name}!"
        )

    text = (
        f"{welcome_text}\n\n"
        "🚀 <b>WiseNation Bot</b>\n\n"
        "Discover collections, monitor wallets, "
        "track NFT activity, and manage your Web3 operations "
        "from Telegram.\n\n"
        "Select an option below to get started."
    )

    await message.answer(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )