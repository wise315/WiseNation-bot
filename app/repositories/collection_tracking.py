from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.collection_tracking import CollectionTracking


class CollectionTrackingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(
        self,
        tracking_id: int,
    ) -> CollectionTracking | None:
        result = await self.session.execute(
            select(CollectionTracking).where(
                CollectionTracking.id == tracking_id
            )
        )

        return result.scalar_one_or_none()

    async def get_by_user_and_contract(
        self,
        user_id: int,
        contract_address: str,
    ) -> CollectionTracking | None:
        result = await self.session.execute(
            select(CollectionTracking).where(
                CollectionTracking.user_id == user_id,
                CollectionTracking.contract_address == contract_address,
            )
        )

        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: int,
        active_only: bool = True,
    ) -> list[CollectionTracking]:
        query = select(CollectionTracking).where(
            CollectionTracking.user_id == user_id
        )

        if active_only:
            query = query.where(
                CollectionTracking.is_active.is_(True)
            )

        query = query.order_by(CollectionTracking.id)

        result = await self.session.execute(query)

        return list(result.scalars().all())

    async def create(
        self,
        user_id: int,
        contract_address: str,
        collection_name: str | None = None,
        blockchain: str = "ethereum",
    ) -> CollectionTracking:
        tracking = CollectionTracking(
            user_id=user_id,
            contract_address=contract_address,
            collection_name=collection_name,
            blockchain=blockchain,
            is_active=True,
        )

        self.session.add(tracking)

        await self.session.flush()

        return tracking

    async def deactivate(
        self,
        tracking: CollectionTracking,
    ) -> CollectionTracking:
        tracking.is_active = False

        await self.session.flush()

        return tracking

    async def activate(
        self,
        tracking: CollectionTracking,
    ) -> CollectionTracking:
        tracking.is_active = True

        await self.session.flush()

        return tracking