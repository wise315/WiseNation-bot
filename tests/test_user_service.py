import pytest
from sqlalchemy import delete, select

from app.database.models import User
from app.database.session import AsyncSessionLocal
from app.services.user_service import UserService


TEST_TELEGRAM_ID = 999999999999


@pytest.mark.asyncio
async def test_user_can_be_created():
    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            select(User).where(
                User.telegram_id == TEST_TELEGRAM_ID
            )
        )

        user = existing.scalar_one_or_none()

        if user:
            await session.delete(user)
            await session.commit()

        service = UserService(session)

        created_user, created = await service.get_or_create_user(
            telegram_id=TEST_TELEGRAM_ID,
            username="stage2_test",
            first_name="Stage2",
        )

        assert created is True
        assert created_user.telegram_id == TEST_TELEGRAM_ID
        assert created_user.username == "stage2_test"
        assert created_user.first_name == "Stage2"
        assert created_user.subscription_tier == "free"
        assert created_user.is_banned is False

        await session.delete(created_user)
        await session.commit()


@pytest.mark.asyncio
async def test_existing_user_is_returned():
    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            select(User).where(
                User.telegram_id == TEST_TELEGRAM_ID
            )
        )

        user = existing.scalar_one_or_none()

        if user:
            await session.delete(user)
            await session.commit()

        service = UserService(session)

        first_user, first_created = await service.get_or_create_user(
            telegram_id=TEST_TELEGRAM_ID,
            username="stage2_test",
            first_name="Stage2",
        )

        second_user, second_created = await service.get_or_create_user(
            telegram_id=TEST_TELEGRAM_ID,
            username="stage2_test",
            first_name="Stage2",
        )

        assert first_created is True
        assert second_created is False

        assert first_user.id == second_user.id

        await session.delete(second_user)
        await session.commit()