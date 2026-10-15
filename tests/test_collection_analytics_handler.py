from app.bot.handlers.collection import (
    _format_analytics_value,
    _format_collection_analytics,
)
from app.bot.keyboards.collection import (
    collection_analytics_keyboard,
    collection_result_keyboard,
)
from app.schemas.collection_analytics import CollectionAnalytics


CONTRACT_ADDRESS = (
    "0x0000000000000000000000000000000000000001"
)


def test_collection_result_keyboard_contains_analytics_button() -> None:
    keyboard = collection_result_keyboard(
        CONTRACT_ADDRESS
    )

    buttons = [
        button
        for row in keyboard.inline_keyboard
        for button in row
    ]

    analytics_button = next(
        button
        for button in buttons
        if (
            button.callback_data
            and button.callback_data.startswith(
                "collections:analytics:"
            )
        )
    )

    assert analytics_button.text == "📊 Analytics"

    assert analytics_button.callback_data == (
        f"collections:analytics:{CONTRACT_ADDRESS}"
    )


def test_collection_analytics_keyboard_contains_refresh() -> None:
    keyboard = collection_analytics_keyboard(
        CONTRACT_ADDRESS
    )

    buttons = [
        button
        for row in keyboard.inline_keyboard
        for button in row
    ]

    callback_data = [
        button.callback_data
        for button in buttons
    ]

    assert (
        f"collections:analytics:{CONTRACT_ADDRESS}"
        in callback_data
    )


def test_format_analytics_value() -> None:
    assert _format_analytics_value(1234) == "1,234"
    assert _format_analytics_value(1234.5) == "1,234.50"
    assert _format_analytics_value(1234.5, " ETH") == (
        "1,234.50 ETH"
    )
    assert _format_analytics_value(None) == "N/A"


def test_format_collection_analytics() -> None:
    analytics = CollectionAnalytics(
        contract_address=CONTRACT_ADDRESS,
        collection_slug="test-collection",
        floor_price=8.5,
        floor_price_currency="ETH",
        one_day_volume=42.35,
        one_day_volume_currency="ETH",
        one_day_sales=17,
        seven_day_volume=183.20,
        seven_day_volume_currency="ETH",
        seven_day_sales=74,
        thirty_day_volume=721.50,
        thirty_day_volume_currency="ETH",
        thirty_day_sales=291,
        total_volume=12450.0,
        total_volume_currency="ETH",
        total_sales=5842,
        num_owners=3421,
        total_supply=10000,
        unique_item_count=10000,
    )

    text = _format_collection_analytics(
        analytics
    )

    assert "📊 <b>Collection Analytics</b>" in text
    assert "test-collection" in text

    assert "8.50 ETH" in text

    assert "42.35 ETH" in text
    assert "Sales: 17" in text

    assert "183.20 ETH" in text
    assert "Sales: 74" in text

    assert "721.50 ETH" in text
    assert "Sales: 291" in text

    assert "12,450.00 ETH" in text
    assert "Sales: 5,842" in text

    assert "3,421" in text
    assert "10,000" in text


def test_format_collection_analytics_with_missing_values() -> None:
    analytics = CollectionAnalytics(
        contract_address=CONTRACT_ADDRESS,
        collection_slug="test-collection",
    )

    text = _format_collection_analytics(
        analytics
    )

    assert "Floor Price" in text
    assert "N/A" in text