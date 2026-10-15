from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="🪙 MINT", callback_data="menu:mint"),
            InlineKeyboardButton(text="🎯 SNIPER", callback_data="menu:sniper"),
        ],
        [
            InlineKeyboardButton(
                text="👀 WALLET TRACKER",
                callback_data="menu:wallet_tracker",
            ),
            InlineKeyboardButton(
                text="📋 COPY TRADING",
                callback_data="menu:copy_trading",
            ),
        ],
        [
            InlineKeyboardButton(text="🛒 MARKET", callback_data="menu:market"),
            InlineKeyboardButton(
                text="💼 PORTFOLIO",
                callback_data="menu:portfolio",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🖼 COLLECTIONS",
                callback_data="menu:collections",
            ),
            InlineKeyboardButton(
                text="🔔 ALERTS",
                callback_data="menu:alerts",
            ),
        ],
        [
            InlineKeyboardButton(
                text="📊 ANALYTICS",
                callback_data="menu:analytics",
            ),
            InlineKeyboardButton(
                text="👛 WALLETS",
                callback_data="menu:wallets",
            ),
        ],
        [
            InlineKeyboardButton(
                text="⚙️ SETTINGS",
                callback_data="menu:settings",
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)