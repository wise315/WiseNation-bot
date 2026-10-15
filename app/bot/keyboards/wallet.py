from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def wallet_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text="📋 My Wallets",
                callback_data="wallets:list",
            ),
        ],
        [
            InlineKeyboardButton(
                text="➕ Add Wallet",
                callback_data="wallets:add",
            ),
        ],
        [
            InlineKeyboardButton(
                text="⭐ Set Default",
                callback_data="wallets:set_default",
            ),
            InlineKeyboardButton(
                text="🗑 Remove",
                callback_data="wallets:remove",
            ),
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Back",
                callback_data="menu:back",
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def wallet_list_keyboard(wallets) -> InlineKeyboardMarkup:
    keyboard = []

    for wallet in wallets:
        short_address = (
            f"{wallet.address[:6]}...{wallet.address[-4:]}"
        )
        label = wallet.label or short_address

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{'⭐ ' if wallet.is_default else ''}{label}",
                    callback_data=f"wallet:view:{wallet.id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Back",
                callback_data="menu:wallets",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def cancel_wallet_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text="❌ Cancel",
                callback_data="wallets:cancel_add",
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def wallet_selection_keyboard(
    wallets,
    action: str,
) -> InlineKeyboardMarkup:
    keyboard = []

    for wallet in wallets:
        short_address = (
            f"{wallet.address[:6]}..."
            f"{wallet.address[-4:]}"
        )

        label = wallet.label or short_address

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{'⭐ ' if wallet.is_default else ''}"
                        f"{label}"
                    ),
                    callback_data=f"wallet:{action}:{wallet.id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="❌ Cancel",
                callback_data="wallets:cancel_action",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def remove_wallet_confirmation_keyboard(
    wallet_id: int,
) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Yes, Remove",
                callback_data=f"wallet:confirm_remove:{wallet_id}",
            ),
            InlineKeyboardButton(
                text="❌ Cancel",
                callback_data="wallets:cancel_action",
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def wallet_details_keyboard(wallet_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text="💰 Token Balances",
                callback_data=f"wallet:tokens:{wallet_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="🖼 NFT Holdings",
                callback_data=f"wallet:nfts:{wallet_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="📜 Transaction History",
                callback_data=f"wallet:transactions:{wallet_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Refresh Balance",
                callback_data=f"wallet:refresh:{wallet_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Back to Wallets",
                callback_data="wallets:list",
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)