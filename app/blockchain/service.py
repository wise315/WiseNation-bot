from app.blockchain.providers.ethereum import EthereumProvider
from app.core.config import get_settings


class BlockchainService:
    def __init__(self):
        settings = get_settings()

        self.ethereum = EthereumProvider(
            settings.ethereum_rpc_http
        )