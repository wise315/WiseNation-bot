from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Wallet


class WalletRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, wallet_id: int) -> Wallet | None:
        result = await self.session.execute(
            select(Wallet).where(Wallet.id == wallet_id)
        )

        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> list[Wallet]:
        result = await self.session.execute(
            select(Wallet)
            .where(Wallet.user_id == user_id)
            .order_by(Wallet.id)
        )

        return list(result.scalars().all())

    async def get_default_by_user_id(
        self,
        user_id: int,
    ) -> Wallet | None:
        result = await self.session.execute(
            select(Wallet).where(
                Wallet.user_id == user_id,
                Wallet.is_default.is_(True),
            )
        )

        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: int,
        chain_id: int,
        address: str,
        label: str | None,
        wallet_type: str,
        encrypted_private_key: str | None,
        is_default: bool = False,
    ) -> Wallet:
        wallet = Wallet(
            user_id=user_id,
            chain_id=chain_id,
            address=address,
            label=label,
            is_default=is_default,
            wallet_type=wallet_type,
            encrypted_private_key=encrypted_private_key,
            created_at=datetime.now(timezone.utc),
        )

        self.session.add(wallet)

        await self.session.flush()

        return wallet

    async def delete(self, wallet_id: int) -> bool:
        result = await self.session.execute(
            delete(Wallet).where(Wallet.id == wallet_id)
        )

        return result.rowcount > 0