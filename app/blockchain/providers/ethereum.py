from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider

from app.blockchain.contracts.erc20 import ERC20Reader


class EthereumProvider:
    def __init__(self, rpc_url: str):
        self.web3 = AsyncWeb3(
            AsyncHTTPProvider(rpc_url)
        )

    async def get_chain_id(self) -> int:
        return await self.web3.eth.chain_id

    async def get_block_number(self) -> int:
        return await self.web3.eth.block_number

    async def is_connected(self) -> bool:
        return await self.web3.is_connected()

    async def get_balance(self, address: str) -> int:
        return await self.web3.eth.get_balance(address)

    def get_erc20_reader(self) -> ERC20Reader:
        return ERC20Reader(self.web3)