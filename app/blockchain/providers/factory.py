from app.blockchain.providers.etherscan import (
    EtherscanTransactionProvider,
)
from app.blockchain.providers.transaction import (
    TransactionHistoryProvider,
)
from app.core.config import get_settings


def create_transaction_history_provider() -> TransactionHistoryProvider:
    settings = get_settings()

    if not settings.etherscan_api_key:
        raise RuntimeError(
            "Etherscan API key is not configured."
        )

    return EtherscanTransactionProvider(
        api_key=settings.etherscan_api_key,
        chain_id=settings.ethereum_chain_id,
    )