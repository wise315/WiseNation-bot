from aiogram import Router
from aiogram.types import CallbackQuery


router = Router()


MODULE_NAMES = {
    "mint": "🪙 MINT",
    "sniper": "🎯 SNIPER",
    "wallet_tracker": "👀 WALLET TRACKER",
    "copy_trading": "📋 COPY TRADING",
    "market": "🛒 MARKET",
    "portfolio": "💼 PORTFOLIO",
    "collections": "🖼 COLLECTIONS",
    "alerts": "🔔 ALERTS",
    "analytics": "📊 ANALYTICS",
    "wallets": "👛 WALLETS",
    "settings": "⚙️ SETTINGS",
}


@router.callback_query(lambda callback: callback.data == "menu:back")
async def menu_back_handler(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.edit_text(
            "Please use /start to open the main menu."
        )

    await callback.answer()


@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("menu:")
        and callback.data != "menu:wallets"
        and callback.data != "menu:collections"
        and callback.data != "menu:back"
    )
)
async def menu_placeholder_handler(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.edit_text(
            "This module will be implemented in a later stage."
        )

    await callback.answer()