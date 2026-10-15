from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.repositories.users import UserRepository


class UserService:
    def __init__(self, session: AsyncSession):
        self.repository = UserRepository(session)

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
    ) -> tuple[User, bool]:
        user = await self.repository.get_by_telegram_id(
            telegram_id
        )

        if user:
            return user, False

        user = await self.repository.create(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )

        await self.repository.session.commit()

        return user, True