from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3

from app.repositories.collection_tracking import (
    CollectionTrackingRepository,
)


class CollectionTrackingService:
    def __init__(self, session: AsyncSession):
        self.repository = CollectionTrackingRepository(session)
        self.session = session

    @staticmethod
    def normalize_contract_address(address: str) -> str:
        normalized_address = address.strip()

        if not Web3.is_address(normalized_address):
            raise ValueError("Invalid Ethereum contract address.")

        return Web3.to_checksum_address(normalized_address)

    async def track_collection(
        self,
        user_id: int,
        contract_address: str,
        collection_name: str | None = None,
        blockchain: str = "ethereum",
    ):
        if blockchain.lower() != "ethereum":
            raise ValueError(
                "Collection tracking currently supports Ethereum only."
            )

        normalized_address = self.normalize_contract_address(
            contract_address
        )

        existing = await self.repository.get_by_user_and_contract(
            user_id=user_id,
            contract_address=normalized_address,
        )

        if existing is not None:
            if existing.is_active:
                return existing

            return await self.repository.activate(existing)

        return await self.repository.create(
            user_id=user_id,
            contract_address=normalized_address,
            collection_name=collection_name.strip()
            if collection_name
            else None,
            blockchain=blockchain.lower(),
        )

    async def untrack_collection(
        self,
        user_id: int,
        contract_address: str,
    ):
        normalized_address = self.normalize_contract_address(
            contract_address
        )

        tracking = await self.repository.get_by_user_and_contract(
            user_id=user_id,
            contract_address=normalized_address,
        )

        if tracking is None:
            return None

        if tracking.is_active:
            await self.repository.deactivate(tracking)

        return tracking

    async def is_tracking(
        self,
        user_id: int,
        contract_address: str,
    ) -> bool:
        normalized_address = self.normalize_contract_address(
            contract_address
        )

        tracking = await self.repository.get_by_user_and_contract(
            user_id=user_id,
            contract_address=normalized_address,
        )

        return tracking is not None and tracking.is_active

    async def get_tracked_collections(
        self,
        user_id: int,
    ):
        return await self.repository.list_by_user(
            user_id=user_id,
            active_only=True,
        )