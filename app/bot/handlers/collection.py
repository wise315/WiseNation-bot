from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database.session import AsyncSessionLocal
from app.services.user_service import UserService
from app.services.collection_tracking_service import (
    CollectionTrackingService,
)
from app.blockchain.address import normalize_ethereum_address
from app.blockchain.providers.collection_factory import create_collection_provider
from app.blockchain.providers.sale_factory import create_sale_provider
from app.blockchain.providers.analytics_factory import (
    create_collection_analytics_provider,
)
from app.schemas.collection_analytics import CollectionAnalytics
from app.bot.keyboards.collection import (
    cancel_collection_keyboard,
    collection_analytics_keyboard,
    collection_menu_keyboard,
    collection_result_keyboard,
    collection_sales_keyboard,
    tracked_collections_keyboard,
)
from app.bot.states.collection import CollectionStates
from app.services.collection_service import CollectionService
from app.schemas.sale import NFTSale

router = Router()


def _short_address(address: str | None) -> str:
    if not address:
        return "N/A"

    if len(address) <= 12:
        return address

    return f"{address[:6]}...{address[-4:]}"


def _format_sale_time(timestamp: datetime | None) -> str:
    if timestamp is None:
        return "Unknown time"

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    timestamp = timestamp.astimezone(timezone.utc)

    return timestamp.strftime("%Y-%m-%d %H:%M UTC")


def _format_sale(sale: NFTSale, number: int) -> str:
    token_id = sale.token_id or "Unknown"

    if sale.price is None:
        price_text = "Price unavailable"
    else:
        currency = sale.currency or "ETH"
        price_text = f"{sale.price:g} {currency}"

    marketplace = sale.marketplace or "Unknown marketplace"

    buyer = _short_address(sale.buyer)
    seller = _short_address(sale.seller)

    sale_time = _format_sale_time(sale.timestamp)

    lines = [
        f"<b>{number}. NFT #{token_id}</b>",
        f"💰 Price: <b>{price_text}</b>",
        f"🏪 Marketplace: {marketplace}",
        f"👤 Buyer: <code>{buyer}</code>",
        f"👤 Seller: <code>{seller}</code>",
        f"🕐 Time: {sale_time}",
    ]

    if sale.transaction_hash:
        lines.append(
            f"🔗 TX: <code>{_short_address(sale.transaction_hash)}</code>"
        )

    return "\n".join(lines)


def _format_sales_message(
    contract_address: str,
    sales: list[NFTSale],
) -> str:
    short_contract = _short_address(contract_address)

    if not sales:
        return (
            "📈 <b>Recent Sales</b>\n\n"
            f"Contract: <code>{short_contract}</code>\n\n"
            "No recent sales were found for this collection."
        )

    sections = [
        "📈 <b>Recent Sales</b>",
        "",
        f"Contract: <code>{short_contract}</code>",
        "",
    ]

    for index, sale in enumerate(sales, start=1):
        sections.append(_format_sale(sale, index))
        sections.append("")

    return "\n".join(sections).rstrip()

def _format_analytics_value(
    value: float | int | None,
    suffix: str = "",
) -> str:
    if value is None:
        return "N/A"

    if isinstance(value, float):
        formatted = f"{value:,.2f}"
    else:
        formatted = f"{value:,}"

    return f"{formatted}{suffix}"


def _format_collection_analytics(
    analytics: CollectionAnalytics,
) -> str:
    floor = (
        f"{analytics.floor_price:,.2f} "
        f"{analytics.floor_price_currency or ''}"
    ).strip() if analytics.floor_price is not None else "N/A"

    one_day_volume = (
        f"{analytics.one_day_volume:,.2f} "
        f"{analytics.one_day_volume_currency or ''}"
    ).strip() if analytics.one_day_volume is not None else "N/A"

    seven_day_volume = (
        f"{analytics.seven_day_volume:,.2f} "
        f"{analytics.seven_day_volume_currency or ''}"
    ).strip() if analytics.seven_day_volume is not None else "N/A"

    thirty_day_volume = (
        f"{analytics.thirty_day_volume:,.2f} "
        f"{analytics.thirty_day_volume_currency or ''}"
    ).strip() if analytics.thirty_day_volume is not None else "N/A"

    total_volume = (
        f"{analytics.total_volume:,.2f} "
        f"{analytics.total_volume_currency or ''}"
    ).strip() if analytics.total_volume is not None else "N/A"

    return (
        "📊 <b>Collection Analytics</b>\n\n"
        f"🔗 <code>{analytics.collection_slug}</code>\n\n"
        "💰 <b>Floor Price</b>\n"
        f"{floor}\n\n"
        "📅 <b>24 Hours</b>\n"
        f"Volume: {one_day_volume}\n"
        f"Sales: {_format_analytics_value(analytics.one_day_sales)}\n\n"
        "📆 <b>7 Days</b>\n"
        f"Volume: {seven_day_volume}\n"
        f"Sales: {_format_analytics_value(analytics.seven_day_sales)}\n\n"
        "📆 <b>30 Days</b>\n"
        f"Volume: {thirty_day_volume}\n"
        f"Sales: {_format_analytics_value(analytics.thirty_day_sales)}\n\n"
        "📈 <b>All Time</b>\n"
        f"Volume: {total_volume}\n"
        f"Sales: {_format_analytics_value(analytics.total_sales)}\n\n"
        "👥 <b>Owners</b>\n"
        f"{_format_analytics_value(analytics.num_owners)}\n\n"
        "🧩 <b>Supply</b>\n"
        f"{_format_analytics_value(analytics.total_supply)}\n\n"
        "🎨 <b>Unique Items</b>\n"
        f"{_format_analytics_value(analytics.unique_item_count)}"
    )


@router.callback_query(lambda callback: callback.data == "menu:collections")
async def collections_menu_handler(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🖼 <b>Collections</b>\n\n"
        "Look up an NFT collection using its Ethereum "
        "contract address.",
        reply_markup=collection_menu_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(lambda callback: callback.data == "collections:lookup")
async def collection_lookup_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.set_state(CollectionStates.waiting_for_contract_address)

    await callback.message.edit_text(
        "🔎 <b>Lookup Collection</b>\n\n"
        "Send the NFT collection's Ethereum contract address.\n\n"
        "Example:\n"
        "<code>0x0000000000000000000000000000000000000001</code>",
        reply_markup=cancel_collection_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(lambda callback: callback.data == "collections:cancel")
async def collection_lookup_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()

    await callback.message.edit_text(
        "🖼 <b>Collections</b>\n\n"
        "Collection lookup cancelled.",
        reply_markup=collection_menu_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()
    

@router.callback_query(
    lambda callback: callback.data == "collections:tracked"
)
async def tracked_collections_handler(
    callback: CallbackQuery,
) -> None:
    if callback.from_user is None or callback.message is None:
        return

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

        tracking_service = CollectionTrackingService(session)

        tracked_collections = (
            await tracking_service.get_tracked_collections(
                user_id=user.id,
            )
        )

    if not tracked_collections:
        await callback.message.edit_text(
            "📋 <b>My Tracked Collections</b>\n\n"
            "You are not tracking any collections yet.\n\n"
            "Open a collection and tap "
            "<b>📌 Track Collection</b> to start tracking it.",
            reply_markup=collection_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    lines = [
        "📋 <b>My Tracked Collections</b>",
        "",
        "Select a collection to view its details:",
        "",
    ]

    for index, collection in enumerate(tracked_collections, start=1):
        name = (
            collection.collection_name
            or _short_address(collection.contract_address)
        )
        lines.append(f"{index}. <b>{name}</b>")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=tracked_collections_keyboard(tracked_collections),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("collections:track:")
    )
)
async def track_collection_handler(
    callback: CallbackQuery,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer(
            "Unable to track collection.",
            show_alert=True,
        )
        return

    contract_address = callback.data.split(
        "collections:track:",
        1,
    )[1]

    try:
        checksum_address = normalize_ethereum_address(contract_address)
    except ValueError:
        await callback.answer(
            "Invalid collection address.",
            show_alert=True,
        )
        return

    await callback.answer("Tracking collection...")

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

        # Tracking is intentionally independent of collection metadata.
        # If a name is not already stored, the UI falls back to the address.
        tracking_service = CollectionTrackingService(session)

        try:
            tracking = await tracking_service.track_collection(
                user_id=user.id,
                contract_address=checksum_address,
            )
            await session.commit()

            # Capture ORM values before leaving the session.
            tracked_contract_address = tracking.contract_address
            tracked_collection_name = (
                tracking.collection_name
                or _short_address(tracking.contract_address)
            )

        except ValueError as exc:
            await session.rollback()

            await callback.message.edit_text(
                f"❌ <b>Unable to Track Collection</b>\n\n{str(exc)}",
                reply_markup=collection_menu_keyboard(),
                parse_mode="HTML",
            )
            return

        except Exception:
            await session.rollback()

            await callback.message.edit_text(
                "❌ <b>Tracking Failed</b>\n\n"
                "We could not track this collection right now.\n"
                "Please try again later.",
                reply_markup=collection_menu_keyboard(),
                parse_mode="HTML",
            )
            return

    await callback.message.edit_text(
        "📌 <b>Collection Tracked</b>\n\n"
        f"Collection: <b>{tracked_collection_name}</b>\n"
        f"Contract: <code>{_short_address(tracked_contract_address)}</code>\n\n"
        "You can now find it under "
        "<b>📋 My Tracked Collections</b>.",
        reply_markup=collection_result_keyboard(
            tracked_contract_address,
            is_tracking=True,
        ),
        parse_mode="HTML",
    )


@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("collections:untrack:")
    )
)
async def untrack_collection_handler(
    callback: CallbackQuery,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer(
            "Unable to untrack collection.",
            show_alert=True,
        )
        return

    contract_address = callback.data.split(
        "collections:untrack:",
        1,
    )[1]

    try:
        checksum_address = normalize_ethereum_address(contract_address)
    except ValueError:
        await callback.answer(
            "Invalid collection address.",
            show_alert=True,
        )
        return

    await callback.answer("Untracking collection...")

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

        tracking_service = CollectionTrackingService(session)

        try:
            tracking = await tracking_service.untrack_collection(
                user_id=user.id,
                contract_address=checksum_address,
            )

            if tracking is None:
                await session.rollback()

                await callback.message.edit_text(
                    "ℹ️ <b>Collection Not Tracked</b>\n\n"
                    "This collection is not currently being tracked.",
                    reply_markup=collection_menu_keyboard(),
                    parse_mode="HTML",
                )
                return

            await session.commit()

            # Capture ORM values before leaving the session.
            untracked_contract_address = tracking.contract_address
            untracked_collection_name = (
                tracking.collection_name
                or _short_address(tracking.contract_address)
            )

        except ValueError as exc:
            await session.rollback()

            await callback.message.edit_text(
                f"❌ <b>Unable to Untrack Collection</b>\n\n{str(exc)}",
                reply_markup=collection_menu_keyboard(),
                parse_mode="HTML",
            )
            return

        except Exception:
            await session.rollback()

            await callback.message.edit_text(
                "❌ <b>Untracking Failed</b>\n\n"
                "We could not untrack this collection right now.\n"
                "Please try again later.",
                reply_markup=collection_menu_keyboard(),
                parse_mode="HTML",
            )
            return

    await callback.message.edit_text(
        "🔕 <b>Collection Untracked</b>\n\n"
        f"Collection: <b>{untracked_collection_name}</b>\n\n"
        "You will no longer see this collection in your "
        "tracked collections.",
        reply_markup=collection_result_keyboard(
            untracked_contract_address,
            is_tracking=False,
        ),
        parse_mode="HTML",
    )


@router.message(CollectionStates.waiting_for_contract_address, F.text)
async def receive_collection_contract_address(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text is None:
        return

    address = message.text.strip()

    try:
        checksum_address = normalize_ethereum_address(address)
    except ValueError:
        await message.answer(
            "❌ <b>Invalid Ethereum contract address.</b>\n\n"
            "Please send a valid Ethereum contract address.\n\n"
            "Example:\n"
            "<code>0x0000000000000000000000000000000000000001</code>",
            reply_markup=cancel_collection_keyboard(),
            parse_mode="HTML",
        )
        return

    await state.clear()

    await message.answer("🔎 Looking up collection...")

    try:
        provider = create_collection_provider()

        service = CollectionService(
            collection_provider=provider,
        )

        collection = await service.get_collection(
            identifier=checksum_address,
        )

    except Exception:
        await message.answer(
            "❌ <b>Collection Lookup Failed</b>\n\n"
            "We could not retrieve collection metadata right now.\n"
            "Please try again later.",
            reply_markup=collection_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    if collection is None:
        await message.answer(
            "❌ <b>Collection Not Found</b>\n\n"
            "No collection metadata was found for this contract address.",
            reply_markup=collection_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    short_address = _short_address(collection.contract_address)

    symbol_text = collection.symbol or "N/A"
    standard_text = collection.token_standard or "Unknown"

    text = (
        "🖼 <b>Collection</b>\n\n"
        f"Name: <b>{collection.name}</b>\n"
        f"Symbol: <b>{symbol_text}</b>\n"
        f"Standard: <b>{standard_text}</b>\n"
        f"Blockchain: <b>{collection.blockchain.title()}</b>\n"
        f"Contract: <code>{short_address}</code>\n"
    )

    if collection.description:
        text += f"\n<b>Description</b>\n{collection.description}\n"

    if collection.image_url:
        text += f"\nImage: {collection.image_url}\n"

    is_tracking = False

    if message.from_user is not None:
        async with AsyncSessionLocal() as session:
            user_service = UserService(session)

            user, _ = await user_service.get_or_create_user(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
            )

            tracking_service = CollectionTrackingService(session)

            is_tracking = await tracking_service.is_tracking(
                user_id=user.id,
                contract_address=collection.contract_address,
            )

    await message.answer(
        text,
        reply_markup=collection_result_keyboard(
            collection.contract_address,
            is_tracking=is_tracking,
        ),
        parse_mode="HTML",
    )


@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("collections:sales:")
    )
)
async def collection_recent_sales_handler(
    callback: CallbackQuery,
) -> None:
    if callback.message is None:
        await callback.answer(
            "Unable to display sales.",
            show_alert=True,
        )
        return

    contract_address = callback.data.split(":", 2)[-1]

    try:
        checksum_address = normalize_ethereum_address(contract_address)
    except ValueError:
        await callback.answer(
            "Invalid collection address.",
            show_alert=True,
        )
        return

    # Acknowledge the Telegram callback immediately.
    await callback.answer("Loading recent sales...")

    await callback.message.edit_text(
        "📈 <b>Recent Sales</b>\n\n"
        "Loading the latest sales...",
        parse_mode="HTML",
    )

    try:
        sale_provider = create_sale_provider()

        service = CollectionService(
            collection_provider=create_collection_provider(),
            sale_provider=sale_provider,
        )

        sales = await service.get_sales(
            contract_address=checksum_address,
            limit=10,
        )

    except Exception:
        await callback.message.edit_text(
            "❌ <b>Recent Sales Unavailable</b>\n\n"
            "We could not retrieve recent sales for this collection right now.\n"
            "Please try again later.",
            reply_markup=collection_sales_keyboard(
                checksum_address,
            ),
            parse_mode="HTML",
        )
        return

    text = _format_sales_message(
        contract_address=checksum_address,
        sales=sales,
    )

    await callback.message.edit_text(
        text,
        reply_markup=collection_sales_keyboard(
            checksum_address,
        ),
        parse_mode="HTML",
    )


@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("collections:view:")
    )
)
async def collection_view_handler(
    callback: CallbackQuery,
) -> None:
    if callback.message is None:
        await callback.answer(
            "Unable to display collection.",
            show_alert=True,
        )
        return

    contract_address = callback.data.split(":", 2)[-1]

    try:
        checksum_address = normalize_ethereum_address(contract_address)
    except ValueError:
        await callback.answer(
            "Invalid collection address.",
            show_alert=True,
        )
        return

    await callback.answer("Loading collection...")

    await callback.message.edit_text(
        "🖼 <b>Collection</b>\n\n"
        "Loading collection details...",
        parse_mode="HTML",
    )

    try:
        provider = create_collection_provider()

        service = CollectionService(
            collection_provider=provider,
        )

        collection = await service.get_collection(
            identifier=checksum_address,
        )

    except Exception:
        await callback.message.edit_text(
            "❌ <b>Collection Unavailable</b>\n\n"
            "We could not retrieve this collection right now.",
            reply_markup=collection_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    if collection is None:
        await callback.message.edit_text(
            "❌ <b>Collection Not Found</b>\n\n"
            "No collection metadata was found for this address.",
            reply_markup=collection_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    short_address = _short_address(collection.contract_address)

    text = (
        "🖼 <b>Collection</b>\n\n"
        f"Name: <b>{collection.name}</b>\n"
        f"Symbol: <b>{collection.symbol or 'N/A'}</b>\n"
        f"Standard: <b>{collection.token_standard or 'Unknown'}</b>\n"
        f"Blockchain: <b>{collection.blockchain.title()}</b>\n"
        f"Contract: <code>{short_address}</code>\n"
    )

    if collection.description:
        text += f"\n<b>Description</b>\n{collection.description}\n"

    if collection.image_url:
        text += f"\nImage: {collection.image_url}\n"

    is_tracking = False

    if callback.from_user is not None:
        async with AsyncSessionLocal() as session:
            user_service = UserService(session)

            user, _ = await user_service.get_or_create_user(
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
            )

            tracking_service = CollectionTrackingService(session)

            is_tracking = await tracking_service.is_tracking(
                user_id=user.id,
                contract_address=collection.contract_address,
            )

    await callback.message.edit_text(
        text,
        reply_markup=collection_result_keyboard(
            collection.contract_address,
            is_tracking=is_tracking,
        ),
        parse_mode="HTML",
    )
    
@router.callback_query(
    F.data.startswith("collections:analytics:")
)
async def collection_analytics_callback(
    callback: CallbackQuery,
) -> None:
    if callback.message is None:
        await callback.answer(
            "Unable to display analytics.",
            show_alert=True,
        )
        return

    contract_address = callback.data.split(
        "collections:analytics:",
        1,
    )[1]

    try:
        checksum_address = normalize_ethereum_address(
            contract_address
        )

        analytics_provider = (
            create_collection_analytics_provider()
        )

        service = CollectionService(
            collection_provider=create_collection_provider(),
            analytics_provider=analytics_provider,
        )

        analytics = await service.get_analytics(
            contract_address=checksum_address,
        )

        if analytics is None:
            is_tracking = False

            if callback.from_user is not None:
                async with AsyncSessionLocal() as session:
                    user_service = UserService(session)

                    user, _ = await user_service.get_or_create_user(
                        telegram_id=callback.from_user.id,
                        username=callback.from_user.username,
                        first_name=callback.from_user.first_name,
                    )

                    tracking_service = CollectionTrackingService(session)

                    is_tracking = await tracking_service.is_tracking(
                        user_id=user.id,
                        contract_address=checksum_address,
                    )

            await callback.message.edit_text(
                "❌ <b>Analytics unavailable</b>\n\n"
                "OpenSea could not find analytics for this "
                "collection.",
                reply_markup=collection_result_keyboard(
                    checksum_address,
                    is_tracking=is_tracking,
                ),
                parse_mode="HTML",
            )
            await callback.answer()
            return

        text = _format_collection_analytics(
            analytics
        )

        await callback.message.edit_text(
            text,
            reply_markup=collection_analytics_keyboard(
                checksum_address
            ),
        )

        await callback.answer()

    except ValueError:
        await callback.message.edit_text(
            "❌ Invalid collection contract address.",
            reply_markup=collection_menu_keyboard(),
        )
        await callback.answer()

    except Exception:
        await callback.message.edit_text(
            "❌ Unable to load collection analytics right now.\n\n"
            "Please try again.",
            reply_markup=collection_menu_keyboard(),
        )
        await callback.answer()