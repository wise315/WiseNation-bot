from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select

from app.database.models import CollectionTracking, User
from app.database.session import AsyncSessionLocal
from app.services.collection_tracking_service import (
    CollectionTrackingService,
)


TEST_TELEGRAM_ID = 999999999995

COLLECTION_ADDRESS = (
    "0x00000000000000000000000000000000000000AA"
)

SECOND_COLLECTION_ADDRESS = (
    "0x00000000000000000000000000000000000000BB"
)


async def create_test_user(session):
    result = await session.execute(
        select(User).where(
            User.telegram_id == TEST_TELEGRAM_ID
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=TEST_TELEGRAM_ID,
            username="collection_tracking_test",
            first_name="CollectionTracking",
            subscription_tier="free",
            is_banned=False,
            created_at=datetime.now(timezone.utc),
        )

        session.add(user)
        await session.flush()

    return user


async def cleanup_test_data(session):
    result = await session.execute(
        select(User).where(
            User.telegram_id == TEST_TELEGRAM_ID
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        return

    await session.execute(
        delete(CollectionTracking).where(
            CollectionTracking.user_id == user.id
        )
    )

    await session.execute(
        delete(User).where(
            User.id == user.id
        )
    )

    await session.commit()


@pytest.mark.asyncio
async def test_track_collection():
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user = await create_test_user(session)

        service = CollectionTrackingService(session)

        tracking = await service.track_collection(
            user_id=user.id,
            contract_address=COLLECTION_ADDRESS,
            collection_name="Test Collection",
        )

        assert tracking.id is not None
        assert tracking.user_id == user.id
        assert tracking.collection_name == "Test Collection"
        assert tracking.blockchain == "ethereum"
        assert tracking.is_active is True

        assert tracking.contract_address == (
            "0x00000000000000000000000000000000000000AA"
        )

        await cleanup_test_data(session)


@pytest.mark.asyncio
async def test_duplicate_tracking_does_not_create_duplicate():
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user = await create_test_user(session)

        service = CollectionTrackingService(session)

        first = await service.track_collection(
            user_id=user.id,
            contract_address=COLLECTION_ADDRESS,
            collection_name="Test Collection",
        )

        second = await service.track_collection(
            user_id=user.id,
            contract_address=COLLECTION_ADDRESS,
            collection_name="Test Collection",
        )

        assert first.id == second.id

        tracked = await service.get_tracked_collections(
            user_id=user.id
        )

        assert len(tracked) == 1

        await cleanup_test_data(session)


@pytest.mark.asyncio
async def test_is_tracking_returns_true_for_active_collection():
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user = await create_test_user(session)

        service = CollectionTrackingService(session)

        await service.track_collection(
            user_id=user.id,
            contract_address=COLLECTION_ADDRESS,
        )

        result = await service.is_tracking(
            user_id=user.id,
            contract_address=COLLECTION_ADDRESS,
        )

        assert result is True

        await cleanup_test_data(session)


@pytest.mark.asyncio
async def test_untrack_collection_deactivates_tracking():
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user = await create_test_user(session)

        service = CollectionTrackingService(session)

        tracking = await service.track_collection(
            user_id=user.id,
            contract_address=COLLECTION_ADDRESS,
        )

        result = await service.untrack_collection(
            user_id=user.id,
            contract_address=COLLECTION_ADDRESS,
        )

        assert result is not None
        assert result.id == tracking.id
        assert result.is_active is False

        assert (
            await service.is_tracking(
                user_id=user.id,
                contract_address=COLLECTION_ADDRESS,
            )
            is False
        )

        await cleanup_test_data(session)


@pytest.mark.asyncio
async def test_tracking_same_collection_after_untrack_reactivates():
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user = await create_test_user(session)

        service = CollectionTrackingService(session)

        first = await service.track_collection(
            user_id=user.id,
            contract_address=COLLECTION_ADDRESS,
        )

        await service.untrack_collection(
            user_id=user.id,
            contract_address=COLLECTION_ADDRESS,
        )

        second = await service.track_collection(
            user_id=user.id,
            contract_address=COLLECTION_ADDRESS,
        )

        assert second.id == first.id
        assert second.is_active is True

        await cleanup_test_data(session)


@pytest.mark.asyncio
async def test_user_can_track_multiple_collections():
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user = await create_test_user(session)

        service = CollectionTrackingService(session)

        await service.track_collection(
            user_id=user.id,
            contract_address=COLLECTION_ADDRESS,
            collection_name="Collection One",
        )

        await service.track_collection(
            user_id=user.id,
            contract_address=SECOND_COLLECTION_ADDRESS,
            collection_name="Collection Two",
        )

        tracked = await service.get_tracked_collections(
            user_id=user.id
        )

        assert len(tracked) == 2

        addresses = {
            item.contract_address
            for item in tracked
        }

        assert (
            "0x00000000000000000000000000000000000000AA"
            in addresses
        )

        assert (
            "0x00000000000000000000000000000000000000bb"
            in addresses
        )

        await cleanup_test_data(session)


@pytest.mark.asyncio
async def test_tracking_is_user_specific():
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user = await create_test_user(session)

        other_user = User(
            telegram_id=999999999994,
            username="other_collection_user",
            first_name="Other",
            subscription_tier="free",
            is_banned=False,
            created_at=datetime.now(timezone.utc),
        )

        session.add(other_user)
        await session.flush()

        service = CollectionTrackingService(session)

        await service.track_collection(
            user_id=user.id,
            contract_address=COLLECTION_ADDRESS,
        )

        assert (
            await service.is_tracking(
                user_id=user.id,
                contract_address=COLLECTION_ADDRESS,
            )
            is True
        )

        assert (
            await service.is_tracking(
                user_id=other_user.id,
                contract_address=COLLECTION_ADDRESS,
            )
            is False
        )

        await session.execute(
            delete(CollectionTracking).where(
                CollectionTracking.user_id.in_(
                    [user.id, other_user.id]
                )
            )
        )

        await session.execute(
            delete(User).where(
                User.id.in_([user.id, other_user.id])
            )
        )

        await session.commit()


@pytest.mark.asyncio
async def test_invalid_contract_address_is_rejected():
    async with AsyncSessionLocal() as session:
        await cleanup_test_data(session)

        user = await create_test_user(session)

        service = CollectionTrackingService(session)

        with pytest.raises(ValueError, match="Invalid Ethereum"):
            await service.track_collection(
                user_id=user.id,
                contract_address="not-an-address",
            )

        await cleanup_test_data(session)