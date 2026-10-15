from decimal import Decimal

from web3 import AsyncWeb3

from app.blockchain.abi.erc20 import ERC20_ABI


class ERC20Reader:
    def __init__(self, web3: AsyncWeb3):
        self.web3 = web3

    async def get_balance(
        self,
        token_address: str,
        wallet_address: str,
    ) -> Decimal:
        token_address = self.web3.to_checksum_address(
            token_address
        )

        wallet_address = self.web3.to_checksum_address(
            wallet_address
        )

        contract = self.web3.eth.contract(
            address=token_address,
            abi=ERC20_ABI,
        )

        raw_balance = await contract.functions.balanceOf(
            wallet_address
        ).call()

        decimals = await contract.functions.decimals().call()

        return Decimal(raw_balance) / (Decimal(10) ** decimals)

    async def get_symbol(
        self,
        token_address: str,
    ) -> str:
        token_address = self.web3.to_checksum_address(
            token_address
        )

        contract = self.web3.eth.contract(
            address=token_address,
            abi=ERC20_ABI,
        )

        return await contract.functions.symbol().call()