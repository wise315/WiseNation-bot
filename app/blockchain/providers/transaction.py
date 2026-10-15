from abc import ABC, abstractmethod

from app.schemas.transaction import WalletTransaction


class TransactionHistoryProvider(ABC):
    @abstractmethod
    async def get_transactions(
        self,
        address: str,
        limit: int = 10,
    ) -> list[WalletTransaction]:
        """Return recent transactions for a wallet address."""
        raise NotImplementedError