from app.bot.keyboards.collection import (
    cancel_collection_keyboard,
    collection_menu_keyboard,
    collection_result_keyboard,
)


def test_collection_menu_keyboard():
    keyboard = collection_menu_keyboard()

    buttons = [
        button
        for row in keyboard.inline_keyboard
        for button in row
    ]

    callback_data = {
        button.callback_data
        for button in buttons
    }

    assert "collections:lookup" in callback_data
    assert "menu:back" in callback_data


def test_cancel_collection_keyboard():
    keyboard = cancel_collection_keyboard()

    buttons = [
        button
        for row in keyboard.inline_keyboard
        for button in row
    ]

    callback_data = {
        button.callback_data
        for button in buttons
    }

    assert "collections:cancel" in callback_data


def test_collection_result_keyboard():
    keyboard = collection_result_keyboard()

    buttons = [
        button
        for row in keyboard.inline_keyboard
        for button in row
    ]

    callback_data = {
        button.callback_data
        for button in buttons
    }

    assert "collections:lookup" in callback_data
    assert "menu:collections" in callback_data