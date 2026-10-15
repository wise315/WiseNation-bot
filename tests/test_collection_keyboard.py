from types import SimpleNamespace

from app.bot.keyboards.collection import (
    collection_menu_keyboard,
    collection_result_keyboard,
    tracked_collections_keyboard,
)


COLLECTION_ADDRESS = (
    "0x00000000000000000000000000000000000000AA"
)


def test_collection_menu_keyboard_has_tracked_collections():
    keyboard = collection_menu_keyboard()

    buttons = [
        button
        for row in keyboard.inline_keyboard
        for button in row
    ]

    callback_data = [button.callback_data for button in buttons]

    assert "collections:lookup" in callback_data
    assert "collections:tracked" in callback_data
    assert "menu:back" in callback_data


def test_collection_result_keyboard_shows_track_button():
    keyboard = collection_result_keyboard(
        contract_address=COLLECTION_ADDRESS,
        is_tracking=False,
    )

    buttons = [
        button
        for row in keyboard.inline_keyboard
        for button in row
    ]

    callback_data = [button.callback_data for button in buttons]
    texts = [button.text for button in buttons]

    assert "📌 Track Collection" in texts
    assert (
        f"collections:track:{COLLECTION_ADDRESS}"
        in callback_data
    )


def test_collection_result_keyboard_shows_untrack_button():
    keyboard = collection_result_keyboard(
        contract_address=COLLECTION_ADDRESS,
        is_tracking=True,
    )

    buttons = [
        button
        for row in keyboard.inline_keyboard
        for button in row
    ]

    callback_data = [button.callback_data for button in buttons]
    texts = [button.text for button in buttons]

    assert "🔕 Untrack Collection" in texts
    assert (
        f"collections:untrack:{COLLECTION_ADDRESS}"
        in callback_data
    )


def test_tracked_collections_keyboard():
    collections = [
        SimpleNamespace(
            collection_name="Test Collection",
            contract_address=COLLECTION_ADDRESS,
        ),
        SimpleNamespace(
            collection_name="Second Collection",
            contract_address=(
                "0x00000000000000000000000000000000000000bb"
            ),
        ),
    ]

    keyboard = tracked_collections_keyboard(collections)

    buttons = [
        button
        for row in keyboard.inline_keyboard
        for button in row
    ]

    callback_data = [button.callback_data for button in buttons]
    texts = [button.text for button in buttons]

    assert "🖼 Test Collection" in texts
    assert "🖼 Second Collection" in texts

    assert (
        f"collections:view:{COLLECTION_ADDRESS}"
        in callback_data
    )

    assert (
        "collections:view:"
        "0x00000000000000000000000000000000000000bb"
        in callback_data
    )

    assert "collections:lookup" in callback_data
    assert "menu:collections" in callback_data