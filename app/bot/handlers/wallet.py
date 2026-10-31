from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.database.models.chain import Chain
from app.blockchain.address import normalize_ethereum_address
from app.blockchain.providers.factory import (
    create_transaction_history_provider,
)
from app.blockchain.providers.nft_factory import (
    create_nft_provider,
)
from app.blockchain.tokens import SUPPORTED_TOKENS
from app.bot.keyboards.wallet import (
    cancel_wallet_keyboard,
    remove_wallet_confirmation_keyboard,
    wallet_details_keyboard,
    wallet_list_keyboard,
    wallet_menu_keyboard,
    wallet_selection_keyboard,
)
from app.bot.states.wallet import AddWalletStates
from app.database.session import AsyncSessionLocal
from app.services.user_service import UserService
from app.services.wallet_service import WalletService



router = Router()


@router.callback_query(lambda callback: callback.data == "menu:wallets")
async def wallets_menu_handler(callback: CallbackQuery) -> None:
    if callback.from_user is None:
        return

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

        wallet_service = WalletService(session)

        wallets = await wallet_service.get_user_wallets(user.id)

    if wallets:
        wallet_lines = []

        for index, wallet in enumerate(wallets, start=1):
            short_address = (
                f"{wallet.address[:6]}..."
                f"{wallet.address[-4:]}"
            )

            default_marker = " ⭐ Default" if wallet.is_default else ""

            wallet_lines.append(
                f"{index}. {short_address}{default_marker}"
            )

        wallets_text = "\n".join(wallet_lines)

        text = (
            "👛 <b>Your Wallets</b>\n\n"
            f"{wallets_text}\n\n"
            "Choose an action below."
        )
    else:
        text = (
            "👛 <b>Your Wallets</b>\n\n"
            "You don't have any wallets yet.\n\n"
            "Add a wallet to get started."
        )

    await callback.message.edit_text(
        text,
        reply_markup=wallet_menu_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()
    

@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("wallet:view:")
    )
)
async def wallet_details_handler(callback: CallbackQuery) -> None:
    if callback.from_user is None:
        return

    try:
        wallet_id = int(callback.data.split(":")[-1])
    except (ValueError, AttributeError):
        await callback.answer(
            "Invalid wallet selection.",
            show_alert=True,
        )
        return

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

        wallet_service = WalletService(session)

        wallet = await wallet_service.get_wallet(
            user_id=user.id,
            wallet_id=wallet_id,
        )

        if wallet is None:
            await callback.answer(
                "Wallet not found.",
                show_alert=True,
            )
            return

        balance = await wallet_service.get_native_balance(
            user_id=user.id,
            wallet_id=wallet_id,
        )

    if balance is None:
        await callback.answer(
            "Unable to retrieve wallet balance.",
            show_alert=True,
        )
        return

    short_address = f"{wallet.address[:6]}...{wallet.address[-4:]}"
    default_text = "⭐ Default Wallet" if wallet.is_default else ""

    balance_text = f"{balance:.4f}"

    text = (
        "💼 <b>Wallet Details</b>\n\n"
        f"Label: <b>{wallet.label or 'No label'}</b>\n"
        f"Address: <code>{short_address}</code>\n\n"
        "⛓ Network: <b>Ethereum</b>\n"
        f"💰 ETH Balance: <b>{balance_text} ETH</b>\n\n"
        f"{default_text}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=wallet_details_keyboard(wallet.id),
        parse_mode="HTML",
    )

    await callback.answer()
    
    
@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("wallet:tokens:")
    )
)
async def wallet_token_balances_handler(
    callback: CallbackQuery,
) -> None:
    if callback.from_user is None:
        return

    try:
        wallet_id = int(callback.data.split(":")[-1])
    except (ValueError, AttributeError):
        await callback.answer(
            "Invalid wallet selection.",
            show_alert=True,
        )
        return

    # Acknowledge immediately so Telegram does not keep
    # displaying the callback loading indicator.
    await callback.answer("Loading token balances...")

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

        wallet_service = WalletService(session)

        wallet = await wallet_service.get_wallet(
            user_id=user.id,
            wallet_id=wallet_id,
        )

        if wallet is None:
            await callback.message.edit_text(
                "❌ <b>Wallet Not Found</b>\n\n"
                "This wallet could not be found.",
                reply_markup=wallet_menu_keyboard(),
                parse_mode="HTML",
            )
            return

        token_balances = []

        for token in SUPPORTED_TOKENS:
            token_balance = await wallet_service.get_token_balance(
                user_id=user.id,
                wallet_id=wallet_id,
                token_address=token.address,
                symbol=token.symbol,
            )

            if token_balance is not None:
                token_balances.append(token_balance)

    if not token_balances:
        await callback.message.edit_text(
            "❌ <b>Token Balances Unavailable</b>\n\n"
            "Unable to retrieve token balances right now.",
            reply_markup=wallet_details_keyboard(wallet.id),
            parse_mode="HTML",
        )
        return

    short_address = f"{wallet.address[:6]}...{wallet.address[-4:]}"

    lines = [
        "💰 <b>Token Balances</b>",
        "",
        f"Wallet: <code>{short_address}</code>",
        "",
    ]

    for token_balance in token_balances:
        lines.extend(
            [
                f"🪙 <b>{token_balance.symbol}</b>",
                (
                    f"Balance: <b>"
                    f"{token_balance.balance:.6f} "
                    f"{token_balance.symbol}"
                    f"</b>"
                ),
                "",
            ]
        )

    text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=wallet_details_keyboard(wallet.id),
        parse_mode="HTML",
    )
    
    
@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("wallet:nfts:")
    )
)
async def wallet_nft_holdings_handler(
    callback: CallbackQuery,
) -> None:
    if callback.from_user is None:
        return

    try:
        wallet_id = int(callback.data.split(":")[-1])
    except (ValueError, AttributeError):
        await callback.answer(
            "Invalid wallet selection.",
            show_alert=True,
        )
        return

    # Acknowledge immediately so Telegram does not keep
    # displaying the callback loading indicator.
    await callback.answer("Loading NFT holdings...")

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

        wallet_service = WalletService(
            session,
            nft_provider=create_nft_provider(),
        )

        wallet = await wallet_service.get_wallet(
            user_id=user.id,
            wallet_id=wallet_id,
        )

        if wallet is None:
            await callback.message.edit_text(
                "❌ <b>Wallet Not Found</b>\n\n"
                "This wallet could not be found.",
                reply_markup=wallet_menu_keyboard(),
                parse_mode="HTML",
            )
            return

        nfts = await wallet_service.get_nfts(
            user_id=user.id,
            wallet_id=wallet_id,
            limit=20,
        )

    if not nfts:
        await callback.message.edit_text(
            "🖼 <b>NFT Holdings</b>\n\n"
            "No NFTs were found for this wallet.",
            reply_markup=wallet_details_keyboard(wallet.id),
            parse_mode="HTML",
        )
        return

    short_address = (
        f"{wallet.address[:6]}..."
        f"{wallet.address[-4:]}"
    )

    lines = [
        "🖼 <b>NFT Holdings</b>",
        "",
        f"Wallet: <code>{short_address}</code>",
        f"Total shown: <b>{len(nfts)}</b>",
        "",
    ]

    for index, nft in enumerate(nfts, start=1):
        collection_name = (
            nft.collection_name
            or "Unknown Collection"
        )

        nft_name = nft.name or f"Token #{nft.token_id}"

        short_contract = (
            f"{nft.contract_address[:6]}..."
            f"{nft.contract_address[-4:]}"
        )

        lines.extend(
            [
                f"🖼 <b>{index}. {nft_name}</b>",
                f"Collection: <b>{collection_name}</b>",
                f"Token ID: <code>{nft.token_id}</code>",
                f"Standard: <b>{nft.token_standard}</b>",
                f"Contract: <code>{short_contract}</code>",
                "",
            ]
        )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=wallet_details_keyboard(wallet.id),
        parse_mode="HTML",
    )    


@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("wallet:transactions:")
    )
)
async def wallet_transaction_history_handler(
    callback: CallbackQuery,
) -> None:
    if callback.from_user is None:
        return

    try:
        wallet_id = int(callback.data.split(":")[-1])
    except (ValueError, AttributeError):
        await callback.answer(
            "Invalid wallet selection.",
            show_alert=True,
        )
        return

    # Acknowledge the Telegram callback immediately.
    await callback.answer("Loading transaction history...")

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

        wallet_service = WalletService(
            session,
            transaction_provider=create_transaction_history_provider(),
        )

        wallet = await wallet_service.get_wallet(
            user_id=user.id,
            wallet_id=wallet_id,
        )

        if wallet is None:
            await callback.message.edit_text(
                "❌ <b>Wallet Not Found</b>\n\n"
                "This wallet could not be found.",
                reply_markup=wallet_menu_keyboard(),
                parse_mode="HTML",
            )
            return

        transactions = await wallet_service.get_transaction_history(
            user_id=user.id,
            wallet_id=wallet_id,
            limit=10,
        )

    if not transactions:
        await callback.message.edit_text(
            "📜 <b>Transaction History</b>\n\n"
            "No transactions were found for this wallet.",
            reply_markup=wallet_details_keyboard(wallet.id),
            parse_mode="HTML",
        )
        return

    short_address = f"{wallet.address[:6]}...{wallet.address[-4:]}"

    lines = [
        "📜 <b>Transaction History</b>",
        "",
        f"Wallet: <code>{short_address}</code>",
        "",
    ]

    for transaction in transactions:
        short_hash = (
            f"{transaction.hash[:8]}..."
            f"{transaction.hash[-6:]}"
        )

        short_from = (
            f"{transaction.from_address[:6]}..."
            f"{transaction.from_address[-4:]}"
        )

        short_to = "Contract"

        if transaction.to_address:
            short_to = (
                f"{transaction.to_address[:6]}..."
                f"{transaction.to_address[-4:]}"
            )

        timestamp_text = "Unknown"

        if transaction.timestamp:
            timestamp_text = transaction.timestamp.strftime(
                "%Y-%m-%d %H:%M UTC"
            )

        lines.extend(
            [
                f"🔗 <code>{short_hash}</code>",
                f"💰 Value: <b>{transaction.value:.6f} ETH</b>",
                f"📤 From: <code>{short_from}</code>",
                f"📥 To: <code>{short_to}</code>",
                f"🧱 Block: <b>{transaction.block_number}</b>",
                f"📅 {timestamp_text}",
                f"📌 Status: <b>{transaction.status}</b>",
                "",
            ]
        )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=wallet_details_keyboard(wallet.id),
        parse_mode="HTML",
    )

@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("wallet:refresh:")
    )
)
async def wallet_refresh_balance_handler(
    callback: CallbackQuery,
) -> None:
    if callback.from_user is None:
        return

    try:
        wallet_id = int(callback.data.split(":")[-1])
    except (ValueError, AttributeError):
        await callback.answer(
            "Invalid wallet selection.",
            show_alert=True,
        )
        return

    # Acknowledge the Telegram callback immediately.
    await callback.answer("Refreshing balance...")

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

        wallet_service = WalletService(session)

        wallet = await wallet_service.get_wallet(
            user_id=user.id,
            wallet_id=wallet_id,
        )

        if wallet is None:
            await callback.message.edit_text(
                "❌ <b>Wallet Not Found</b>\n\n"
                "This wallet could not be found.",
                reply_markup=wallet_menu_keyboard(),
                parse_mode="HTML",
            )
            return

        balance = await wallet_service.get_native_balance(
            user_id=user.id,
            wallet_id=wallet_id,
        )

    if balance is None:
        await callback.message.edit_text(
            "❌ <b>Balance Unavailable</b>\n\n"
            "Unable to retrieve the wallet balance right now.",
            reply_markup=wallet_details_keyboard(wallet.id),
            parse_mode="HTML",
        )
        return

    short_address = f"{wallet.address[:6]}...{wallet.address[-4:]}"
    default_text = "⭐ Default Wallet" if wallet.is_default else ""

    text = (
        "💼 <b>Wallet Details</b>\n\n"
        f"Label: <b>{wallet.label or 'No label'}</b>\n"
        f"Address: <code>{short_address}</code>\n\n"
        "⛓ Network: <b>Ethereum</b>\n"
        f"💰 ETH Balance: <b>{balance:.4f} ETH</b>\n\n"
        f"{default_text}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=wallet_details_keyboard(wallet.id),
        parse_mode="HTML",
    )


@router.callback_query(
    lambda callback: callback.data == "wallets:list"
)
async def wallets_list_handler(callback: CallbackQuery) -> None:
    if callback.from_user is None:
        return

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

        wallet_service = WalletService(session)

        wallets = await wallet_service.get_user_wallets(user.id)

    if not wallets:
        await callback.message.edit_text(
            "📋 <b>My Wallets</b>\n\n"
            "You don't have any wallets yet.",
            reply_markup=wallet_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    lines = [
        "📋 <b>My Wallets</b>",
        "",
        "Select a wallet to view its details:",
    ]

    for wallet in wallets:
        short_address = f"{wallet.address[:6]}...{wallet.address[-4:]}"
        default_marker = " ⭐" if wallet.is_default else ""

        lines.append(
            f"• {wallet.label or short_address}"
            f"{default_marker}"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=wallet_list_keyboard(wallets),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(lambda callback: callback.data == "wallets:add")
async def add_wallet_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.set_state(AddWalletStates.waiting_for_address)

    await callback.message.edit_text(
        "➕ <b>Add Wallet</b>\n\n"
        "Send the Ethereum wallet address you want to track.\n\n"
        "Example:\n"
        "<code>0x0000000000000000000000000000000000000001</code>\n\n"
        "This will be added as a <b>watch-only</b> wallet.",
        reply_markup=cancel_wallet_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(lambda callback: callback.data == "wallets:cancel_add")
async def cancel_add_wallet(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()

    await callback.message.edit_text(
        "👛 <b>Wallet operation cancelled.</b>\n\n"
        "Choose an option below.",
        reply_markup=wallet_menu_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()


@router.message(AddWalletStates.waiting_for_address, F.text)
async def receive_wallet_address(
    message: Message,
    state: FSMContext,
) -> None:
    address = message.text.strip()

    try:
        checksum_address = normalize_ethereum_address(address)
    except ValueError:
        await message.answer(
            "❌ <b>Invalid Ethereum address.</b>\n\n"
            "Please send a valid Ethereum wallet address.\n\n"
            "Example:\n"
            "<code>0x0000000000000000000000000000000000000001</code>",
            reply_markup=cancel_wallet_keyboard(),
            parse_mode="HTML",
        )
        return

    await state.update_data(address=checksum_address)
    await state.set_state(AddWalletStates.waiting_for_label)

    await message.answer(
        "✅ Wallet address accepted.\n\n"
        "Now enter a label for this wallet.\n\n"
        "For example:\n"
        "<code>Main Wallet</code>\n\n"
        "You can also send /skip to continue without a label.",
        reply_markup=cancel_wallet_keyboard(),
        parse_mode="HTML",
    )


@router.message(AddWalletStates.waiting_for_label, F.text)
async def receive_wallet_label(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text is None:
        return

    label = message.text.strip()

    if label == "/skip":
        label = None

    if label and len(label) > 100:
        await message.answer(
            "❌ The wallet label is too long.\n\n"
            "Please use 100 characters or fewer.",
            reply_markup=cancel_wallet_keyboard(),
        )
        return

    data = await state.get_data()
    address = data.get("address")

    if not address:
        await state.clear()

        await message.answer(
            "❌ The wallet address could not be found.\n\n"
            "Please start the Add Wallet process again.",
            reply_markup=wallet_menu_keyboard(),
        )
        return

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )

        wallet_service = WalletService(session)
        
        result = await session.execute(
            select(Chain).where(Chain.chain_id == 1)
        )
        
        ethereum_chain = result.scalar_one_or_none()
        
        if ethereum_chain is None:
            await message.answer(
                "❌ Ethereum network configuration is missing."
                "Please contact the bot administrator."
            )
            return

        wallet = await wallet_service.add_wallet(
            user_id=user.id,
            chain_id=ethereum_chain.id,
            address=address,
            label=label,
            wallet_type="watch_only",
            encrypted_private_key=None,
        )

    await state.clear()

    short_address = (
        f"{wallet.address[:6]}..."
        f"{wallet.address[-4:]}"
    )

    default_text = "\n⭐ This is now your default wallet." if wallet.is_default else ""

    label_text = wallet.label if wallet.label else "No label"

    await message.answer(
        "✅ <b>Wallet Added Successfully</b>\n\n"
        f"Address: <code>{short_address}</code>\n"
        f"Label: {label_text}\n"
        "Type: watch-only"
        f"{default_text}\n\n"
        "Your wallet is now available in the Wallets module.",
        reply_markup=wallet_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(lambda callback: callback.data == "wallets:set_default")
async def set_default_wallet_start(
    callback: CallbackQuery,
) -> None:
    if callback.from_user is None:
        return

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

        wallet_service = WalletService(session)

        wallets = await wallet_service.get_user_wallets(user.id)

    if not wallets:
        await callback.message.edit_text(
            "⭐ <b>Set Default Wallet</b>\n\n"
            "You don't have any wallets yet.\n\n"
            "Add a wallet first.",
            reply_markup=wallet_menu_keyboard(),
            parse_mode="HTML",
        )

        await callback.answer()
        return

    await callback.message.edit_text(
        "⭐ <b>Set Default Wallet</b>\n\n"
        "Select the wallet you want to make your default wallet:",
        reply_markup=wallet_selection_keyboard(
            wallets,
            "set_default",
        ),
        parse_mode="HTML",
    )

    await callback.answer()
    
@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("wallet:set_default:")
    )
)
async def set_default_wallet_handler(
    callback: CallbackQuery,
) -> None:
    if callback.from_user is None:
        return

    try:
        wallet_id = int(callback.data.split(":")[-1])
    except (ValueError, AttributeError):
        await callback.answer(
            "Invalid wallet selection.",
            show_alert=True,
        )
        return

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

        wallet_service = WalletService(session)

        wallet = await wallet_service.set_default_wallet(
            user_id=user.id,
            wallet_id=wallet_id,
        )

    if wallet is None:
        await callback.answer(
            "Wallet not found.",
            show_alert=True,
        )
        return

    short_address = (
        f"{wallet.address[:6]}..."
        f"{wallet.address[-4:]}"
    )

    await callback.message.edit_text(
        "⭐ <b>Default Wallet Updated</b>\n\n"
        f"Wallet: <code>{short_address}</code>\n"
        f"Label: {wallet.label or 'No label'}\n\n"
        "This wallet is now your default wallet.",
        reply_markup=wallet_menu_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()
    
@router.callback_query(
    lambda callback: callback.data == "wallets:cancel_action"
)
async def cancel_wallet_action(
    callback: CallbackQuery,
) -> None:
    await callback.message.edit_text(
        "👛 <b>Wallet operation cancelled.</b>\n\n"
        "Choose an option below.",
        reply_markup=wallet_menu_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()
    
@router.callback_query(
    lambda callback: callback.data == "wallets:remove"
)
async def remove_wallet_start(
    callback: CallbackQuery,
) -> None:
    if callback.from_user is None:
        return

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

        wallet_service = WalletService(session)

        wallets = await wallet_service.get_user_wallets(user.id)

    if not wallets:
        await callback.message.edit_text(
            "🗑 <b>Remove Wallet</b>\n\n"
            "You don't have any wallets to remove.",
            reply_markup=wallet_menu_keyboard(),
            parse_mode="HTML",
        )

        await callback.answer()
        return

    await callback.message.edit_text(
        "🗑 <b>Remove Wallet</b>\n\n"
        "Select the wallet you want to remove:",
        reply_markup=wallet_selection_keyboard(
            wallets,
            "remove",
        ),
        parse_mode="HTML",
    )

    await callback.answer()
    
@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("wallet:remove:")
    )
)
async def remove_wallet_confirmation(
    callback: CallbackQuery,
) -> None:
    if callback.from_user is None:
        return

    try:
        wallet_id = int(callback.data.split(":")[-1])
    except (ValueError, AttributeError):
        await callback.answer(
            "Invalid wallet selection.",
            show_alert=True,
        )
        return

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

        wallet_service = WalletService(session)

        wallet = await wallet_service.get_wallet(
            user_id=user.id,
            wallet_id=wallet_id,
        )

    if wallet is None:
        await callback.answer(
            "Wallet not found.",
            show_alert=True,
        )
        return

    short_address = (
        f"{wallet.address[:6]}..."
        f"{wallet.address[-4:]}"
    )

    await callback.message.edit_text(
        "⚠️ <b>Confirm Wallet Removal</b>\n\n"
        f"Address: <code>{short_address}</code>\n"
        f"Label: {wallet.label or 'No label'}\n\n"
        "Are you sure you want to remove this wallet?",
        reply_markup=remove_wallet_confirmation_keyboard(
            wallet_id
        ),
        parse_mode="HTML",
    )

    await callback.answer()
    
@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("wallet:confirm_remove:")
    )
)
async def remove_wallet_handler(
    callback: CallbackQuery,
) -> None:
    if callback.from_user is None:
        return

    try:
        wallet_id = int(callback.data.split(":")[-1])
    except (ValueError, AttributeError):
        await callback.answer(
            "Invalid wallet selection.",
            show_alert=True,
        )
        return

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)

        user, _ = await user_service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

        wallet_service = WalletService(session)

        removed = await wallet_service.remove_wallet(
            user_id=user.id,
            wallet_id=wallet_id,
        )

    if not removed:
        await callback.answer(
            "Wallet could not be removed.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "✅ <b>Wallet Removed</b>\n\n"
        "The wallet has been removed from your wallet list.",
        reply_markup=wallet_menu_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()