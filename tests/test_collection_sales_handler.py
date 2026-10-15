from datetime import datetime, timezone

from app.bot.handlers.collection import (
    _format_sale,
    _format_sales_message,
)
from app.bot.keyboards.collection import (
    collection_result_keyboard,
    collection_sales_keyboard,
)
from app.schemas.sale import NFTSale


CONTRACT_ADDRESS = (
    "0x0000000000000000000000000000000000000001"
)


def test_collection_result_keyboard_contains_recent_sales_button() -> None:
    keyboard = collection_result_keyboard(
        CONTRACT_ADDRESS
    )

    buttons = [
        button
        for row in keyboard.inline_keyboard
        for button in row
    ]

    sales_button = next(
        button
        for button in buttons
        if (
            button.callback_data
            and button.callback_data.startswith(
                "collections:sales:"
            )
        )
    )

    assert sales_button.text == "📈 Recent Sales"

    assert sales_button.callback_data == (
        f"collections:sales:{CONTRACT_ADDRESS}"
    )


def test_collection_sales_keyboard_contains_refresh_button() -> None:
    keyboard = collection_sales_keyboard(
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
        f"collections:sales:{CONTRACT_ADDRESS}"
        in callback_data
    )


def test_format_opensea_sale() -> None:
    sale = NFTSale(
        contract_address=CONTRACT_ADDRESS,
        token_id="123",
        price=2.5,
        currency="ETH",
        buyer=(
            "0x0000000000000000000000000000000000000002"
        ),
        seller=(
            "0x0000000000000000000000000000000000000003"
        ),
        marketplace="OpenSea",
        transaction_hash=(
            "0x00000000000000000000000000000000000000000000000000000000000000ab"
        ),
        timestamp=datetime(
            2026,
            9,
            20,
            12,
            30,
            tzinfo=timezone.utc,
        ),
    )

    text = _format_sale(
        sale,
        1,
    )

    assert "NFT #123" in text
    assert "2.5 ETH" in text
    assert "OpenSea" in text
    assert "2026-09-20 12:30 UTC" in text

    assert "0x0000...0002" in text
    assert "0x0000...0003" in text

    assert "0x0000...00ab" in text


def test_format_sales_message() -> None:
    sales = [
        NFTSale(
            contract_address=CONTRACT_ADDRESS,
            token_id="456",
            price=1.75,
            currency="ETH",
            buyer=(
                "0x0000000000000000000000000000000000000002"
            ),
            seller=(
                "0x0000000000000000000000000000000000000003"
            ),
            marketplace="OpenSea",
        ),
        NFTSale(
            contract_address=CONTRACT_ADDRESS,
            token_id="789",
            price=3.25,
            currency="ETH",
            marketplace="OpenSea",
        ),
    ]

    text = _format_sales_message(
        contract_address=CONTRACT_ADDRESS,
        sales=sales,
    )

    assert "📈 <b>Recent Sales</b>" in text

    assert "NFT #456" in text
    assert "1.75 ETH" in text

    assert "NFT #789" in text
    assert "3.25 ETH" in text

    assert "OpenSea" in text


def test_format_empty_sales_message() -> None:
    text = _format_sales_message(
        contract_address=CONTRACT_ADDRESS,
        sales=[],
    )

    assert "Recent Sales" in text
    assert "No recent sales were found" in text