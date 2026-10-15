from app.bot.handlers.wallet import router as wallet_router
from app.bot.keyboards.wallet import wallet_menu_keyboard


def test_wallet_router_exists():
    assert wallet_router is not None


def test_wallet_menu_keyboard_has_buttons():
    keyboard = wallet_menu_keyboard()

    buttons = [
        button
        for row in keyboard.inline_keyboard
        for button in row
    ]

    callback_data = {
        button.callback_data
        for button in buttons
    }

    assert "wallets:list" in callback_data
    assert "wallets:add" in callback_data
    assert "wallets:set_default" in callback_data
    assert "wallets:remove" in callback_data
    assert "menu:back" in callback_data
    
    
def test_wallet_details_keyboard_has_transaction_history():
    from app.bot.keyboards.wallet import wallet_details_keyboard

    keyboard = wallet_details_keyboard(wallet_id=123)

    buttons = [
        button
        for row in keyboard.inline_keyboard
        for button in row
    ]

    callback_data = {
        button.callback_data
        for button in buttons
    }

    assert "wallet:transactions:123" in callback_data
    
def test_wallet_details_keyboard_has_nft_holdings():
    from app.bot.keyboards.wallet import wallet_details_keyboard

    keyboard = wallet_details_keyboard(wallet_id=123)

    buttons = [
        button
        for row in keyboard.inline_keyboard
        for button in row
    ]

    callback_data = {
        button.callback_data
        for button in buttons
    }

    assert "wallet:nfts:123" in callback_data