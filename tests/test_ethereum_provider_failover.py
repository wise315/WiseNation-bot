
import pytest

from app.blockchain.providers.ethereum import EthereumProvider


class FakeProvider:
    def __init__(self, name, failures_remaining=0, connected=True):
        self.name = name
        self.failures_remaining = failures_remaining
        self.connected = connected
        self.attempts = 0

    async def is_connected(self):
        return self.connected

    async def request(self):
        self.attempts += 1

        if self.failures_remaining > 0:
            self.failures_remaining -= 1
            raise ConnectionError(f"{self.name} RPC unavailable")

        return f"{self.name} response"


@pytest.fixture
def provider():
    instance = EthereumProvider(
        rpc_url="https://primary.example",
        backup_rpc_url="https://backup.example",
        max_retries=3,
        retry_delay=0.001,
    )

    instance._primary_web3 = FakeProvider("primary")
    instance._backup_web3 = FakeProvider("backup")
    instance.web3 = instance._primary_web3

    return instance


@pytest.mark.asyncio
async def test_primary_rpc_retries_and_recovers(provider):
    provider._primary_web3.failures_remaining = 2

    async def operation(web3):
        return await web3.request()

    result = await provider._execute(operation)

    assert result == "primary response"
    assert provider._primary_web3.attempts == 3
    assert provider._using_backup is False


@pytest.mark.asyncio
async def test_provider_switches_to_backup_when_primary_fails(provider):
    provider._primary_web3.failures_remaining = 3

    async def operation(web3):
        return await web3.request()

    result = await provider._execute(operation)

    assert result == "backup response"
    assert provider._primary_web3.attempts == 3
    assert provider._backup_web3.attempts == 1
    assert provider.web3 is provider._backup_web3
    assert provider._using_backup is True


@pytest.mark.asyncio
async def test_provider_switches_back_to_primary_after_recovery(provider):
    provider._primary_web3.failures_remaining = 3

    async def operation(web3):
        return await web3.request()

    # First request: primary fails and backup succeeds.
    first_result = await provider._execute(operation)

    assert first_result == "backup response"
    assert provider._using_backup is True

    # Simulate primary RPC recovering.
    provider._primary_web3.connected = True
    provider._primary_web3.failures_remaining = 0

    # Second request should detect recovery and use primary.
    second_result = await provider._execute(operation)

    assert second_result == "primary response"
    assert provider.web3 is provider._primary_web3
    assert provider._using_backup is False
