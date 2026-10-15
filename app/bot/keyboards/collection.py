from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def collection_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔎 Lookup Collection",
                callback_data="collections:lookup",
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 My Tracked Collections",
                callback_data="collections:tracked",
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Back",
                callback_data="menu:back",
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def cancel_collection_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text="❌ Cancel",
                callback_data="collections:cancel",
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def collection_result_keyboard(
    contract_address: str | None = None,
    is_tracking: bool = False,
) -> InlineKeyboardMarkup:
    keyboard = []

    if contract_address:
        tracking_text = (
            "🔕 Untrack Collection"
            if is_tracking
            else "📌 Track Collection"
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=tracking_text,
                    callback_data=(
                        f"collections:untrack:{contract_address}"
                        if is_tracking
                        else f"collections:track:{contract_address}"
                    ),
                )
            ]
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    text="📈 Recent Sales",
                    callback_data=(
                        f"collections:sales:{contract_address}"
                    ),
                )
            ]
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    text="📊 Analytics",
                    callback_data=(
                        f"collections:analytics:{contract_address}"
                    ),
                )
            ]
        )

    keyboard.extend(
        [
            [
                InlineKeyboardButton(
                    text="🔎 Lookup Another",
                    callback_data="collections:lookup",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Collections",
                    callback_data="menu:collections",
                )
            ],
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def collection_sales_keyboard(
    contract_address: str,
) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔄 Refresh Sales",
                callback_data=(
                    f"collections:sales:{contract_address}"
                ),
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Collection",
                callback_data=(
                    f"collections:view:{contract_address}"
                ),
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Collections",
                callback_data="menu:collections",
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def collection_analytics_keyboard(
    contract_address: str,
) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔄 Refresh Analytics",
                callback_data=(
                    f"collections:analytics:{contract_address}"
                ),
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Collection",
                callback_data=(
                    f"collections:view:{contract_address}"
                ),
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Collections",
                callback_data="menu:collections",
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def tracked_collections_keyboard(
    collections: list,
) -> InlineKeyboardMarkup:
    keyboard = []

    for collection in collections:
        name = (
            collection.collection_name
            or collection.contract_address[:6]
            + "..."
            + collection.contract_address[-4:]
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🖼 {name}",
                    callback_data=(
                        f"collections:view:{collection.contract_address}"
                    ),
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="🔎 Lookup Collection",
                callback_data="collections:lookup",
            )
        ]
    )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Collections",
                callback_data="menu:collections",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)