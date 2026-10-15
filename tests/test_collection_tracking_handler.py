import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.bot.handlers.collection import (
    track_collection_handler,
    untrack_collection_handler,
    tracked_collections_handler,
)
from app.database.models import User


COLLECTION_ADDRESS = (
    "0x00000000000000000000000000000000000000AA"
)


def create_callback(
    data: str,
    telegram_id: int = 123456789,
):
    callback = MagicMock()

    callback.data = data

    callback.from_user = MagicMock()
    callback.from_user.id = telegram_id
    callback.from_user.username = "test_user"
    callback.from_user.first_name = "Test"

    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()

    callback.answer = AsyncMock()

    return callback


@pytest.mark.asyncio
async def test_track_collection_handler():
    callback = create_callback(
        f"collections:track:{COLLECTION_ADDRESS}"
    )

    tracking = MagicMock()
    tracking.contract_address = COLLECTION_ADDRESS
    tracking.collection_name = "Test Collection"

    user = MagicMock(spec=User)
    user.id = 1

    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    mock_user_service = MagicMock()
    mock_user_service.get_or_create_user = AsyncMock(
        return_value=(user, False)
    )

    mock_tracking_service = MagicMock()
    mock_tracking_service.track_collection = AsyncMock(
        return_value=tracking
    )

    mock_collection = MagicMock()
    mock_collection.name = "Test Collection"

    mock_collection_service = MagicMock()
    mock_collection_service.get_collection = AsyncMock(
        return_value=mock_collection
    )

    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(
        return_value=session
    )
    session_context.__aexit__ = AsyncMock(
        return_value=None
    )

    with (
        patch(
            "app.bot.handlers.collection.AsyncSessionLocal",
            return_value=session_context,
        ),
        patch(
            "app.bot.handlers.collection.UserService",
            return_value=mock_user_service,
        ),
        patch(
            "app.bot.handlers.collection.CollectionTrackingService",
            return_value=mock_tracking_service,
        ),
        patch(
            "app.bot.handlers.collection.create_collection_provider",
        ),
        patch(
            "app.bot.handlers.collection.CollectionService",
            return_value=mock_collection_service,
        ),
    ):
        await track_collection_handler(callback)

    mock_tracking_service.track_collection.assert_awaited_once()

    session.commit.assert_awaited_once()

    callback.message.edit_text.assert_awaited_once()

    call_text = callback.message.edit_text.await_args.args[0]

    assert "Collection Tracked" in call_text
    assert "Test Collection" in call_text


@pytest.mark.asyncio
async def test_untrack_collection_handler():
    callback = create_callback(
        f"collections:untrack:{COLLECTION_ADDRESS}"
    )

    tracking = MagicMock()
    tracking.contract_address = COLLECTION_ADDRESS
    tracking.collection_name = "Test Collection"

    user = MagicMock(spec=User)
    user.id = 1

    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    mock_user_service = MagicMock()
    mock_user_service.get_or_create_user = AsyncMock(
        return_value=(user, False)
    )

    mock_tracking_service = MagicMock()
    mock_tracking_service.untrack_collection = AsyncMock(
        return_value=tracking
    )

    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(
        return_value=session
    )
    session_context.__aexit__ = AsyncMock(
        return_value=None
    )

    with (
        patch(
            "app.bot.handlers.collection.AsyncSessionLocal",
            return_value=session_context,
        ),
        patch(
            "app.bot.handlers.collection.UserService",
            return_value=mock_user_service,
        ),
        patch(
            "app.bot.handlers.collection.CollectionTrackingService",
            return_value=mock_tracking_service,
        ),
    ):
        await untrack_collection_handler(callback)

    mock_tracking_service.untrack_collection.assert_awaited_once()

    session.commit.assert_awaited_once()

    callback.message.edit_text.assert_awaited_once()

    call_text = callback.message.edit_text.await_args.args[0]

    assert "Collection Untracked" in call_text
    assert "Test Collection" in call_text


@pytest.mark.asyncio
async def test_tracked_collections_handler():
    callback = create_callback(
        "collections:tracked"
    )

    user = MagicMock(spec=User)
    user.id = 1

    tracking_one = MagicMock()
    tracking_one.collection_name = "Collection One"
    tracking_one.contract_address = COLLECTION_ADDRESS

    tracking_two = MagicMock()
    tracking_two.collection_name = "Collection Two"
    tracking_two.contract_address = (
        "0x00000000000000000000000000000000000000bb"
    )

    session = MagicMock()

    mock_user_service = MagicMock()
    mock_user_service.get_or_create_user = AsyncMock(
        return_value=(user, False)
    )

    mock_tracking_service = MagicMock()
    mock_tracking_service.get_tracked_collections = AsyncMock(
        return_value=[
            tracking_one,
            tracking_two,
        ]
    )

    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(
        return_value=session
    )
    session_context.__aexit__ = AsyncMock(
        return_value=None
    )

    with (
        patch(
            "app.bot.handlers.collection.AsyncSessionLocal",
            return_value=session_context,
        ),
        patch(
            "app.bot.handlers.collection.UserService",
            return_value=mock_user_service,
        ),
        patch(
            "app.bot.handlers.collection.CollectionTrackingService",
            return_value=mock_tracking_service,
        ),
    ):
        await tracked_collections_handler(callback)

    mock_tracking_service.get_tracked_collections.assert_awaited_once_with(
        user_id=1,
    )

    callback.message.edit_text.assert_awaited_once()

    call_text = callback.message.edit_text.await_args.args[0]

    assert "My Tracked Collections" in call_text
    assert "Collection One" in call_text
    assert "Collection Two" in call_text