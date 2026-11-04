import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider

from app.blockchain.contracts.erc20 import ERC20Reader


logger = logging.getLogger(__name__)

T = TypeVar("T")


class EthereumProvider:
    def __init__(
        self,
        rpc_url: str,
        backup_rpc_url: str = "",
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        if not rpc_url:
            raise ValueError("Primary Ethereum RPC URL is required.")

        if max_retries < 1:
            raise ValueError("max_retries must be at least 1.")

        if retry_delay <= 0:
            raise ValueError("retry_delay must be positive.")

        self.primary_rpc_url = rpc_url
        self.backup_rpc_url = backup_rpc_url or None
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self._primary_web3 = self._create_web3(rpc_url)

        self._backup_web3 = (
            self._create_web3(backup_rpc_url)
            if backup_rpc_url
            else None
        )

        self.web3 = self._primary_web3
        self._using_backup = False

    @staticmethod
    def _create_web3(rpc_url: str) -> AsyncWeb3:
        return AsyncWeb3(
            AsyncHTTPProvider(rpc_url)
        )

    async def _retry(
        self,
        operation: Callable[[AsyncWeb3], Awaitable[T]],
        provider: AsyncWeb3,
        provider_name: str,
    ) -> T:
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return await operation(provider)

            except asyncio.CancelledError:
                raise

            except Exception as exc:
                last_error = exc

                logger.warning(
                    "%s Ethereum RPC attempt %s/%s failed: %s",
                    provider_name,
                    attempt + 1,
                    self.max_retries,
                    exc,
                )

                if attempt + 1 < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)

                    logger.info(
                        "Retrying %s Ethereum RPC in %.1f seconds.",
                        provider_name,
                        delay,
                    )

                    await asyncio.sleep(delay)

        raise last_error

    async def _try_primary_recovery(self) -> bool:
        if not self._using_backup:
            return True

        try:
            connected = await self._primary_web3.is_connected()

            if connected:
                logger.info(
                    "Primary Ethereum RPC has recovered. "
                    "Switching back to primary."
                )

                self.web3 = self._primary_web3
                self._using_backup = False
                return True

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.debug(
                "Primary Ethereum RPC is still unavailable.",
                exc_info=True,
            )

        return False

    async def _execute(
        self,
        operation: Callable[[AsyncWeb3], Awaitable[T]],
    ) -> T:
        # If currently on backup, check whether primary has recovered.
        if self._using_backup:
            await self._try_primary_recovery()

        if not self._using_backup:
            try:
                return await self._retry(
                    operation,
                    self._primary_web3,
                    "Primary",
                )

            except asyncio.CancelledError:
                raise

            except Exception:
                if self._backup_web3 is None:
                    raise

                logger.error(
                    "Primary Ethereum RPC failed. "
                    "Switching to backup RPC.",
                    exc_info=True,
                )

        if self._backup_web3 is None:
            raise RuntimeError(
                "No backup Ethereum RPC provider is configured."
            )

        result = await self._retry(
            operation,
            self._backup_web3,
            "Backup",
        )

        self.web3 = self._backup_web3
        self._using_backup = True

        return result

    async def get_block(
        self,
        block_number: int,
        full_transactions: bool = False,
    ) -> Any:
        if (
            not isinstance(block_number, int)
            or isinstance(block_number, bool)
            or block_number < 0
        ):
            raise ValueError("Invalid block number.")

        return await self._execute(
            lambda web3: web3.eth.get_block(
                block_number,
                full_transactions=full_transactions,
            )
        )

    async def get_logs(
        self,
        filters: dict[str, Any],
    ) -> list:
        return await self._execute(
            lambda web3: web3.eth.get_logs(filters)
        )

    async def get_chain_id(self) -> int:
        return await self._execute(
            lambda web3: web3.eth.chain_id
        )

    async def get_block_number(self) -> int:
        return await self._execute(
            lambda web3: web3.eth.block_number
        )

    async def is_connected(self) -> bool:
        try:
            return await self._execute(
                lambda web3: web3.is_connected()
            )
        except Exception:
            return False

    async def get_balance(self, address: str) -> int:
        return await self._execute(
            lambda web3: web3.eth.get_balance(address)
        )

    def get_erc20_reader(self) -> ERC20Reader:
        return ERC20Reader(self.web3)

    async def close(self) -> None:
        """Close HTTP sessions for primary and backup RPC providers."""

        providers = [self._primary_web3]

        if self._backup_web3 is not None:
            providers.append(self._backup_web3)

        for provider in providers:
            try:
                await provider.provider.disconnect()
                logger.info("Ethereum RPC provider session closed.")

            except Exception:
                logger.exception(
                    "Failed to close Ethereum RPC provider session."
                )