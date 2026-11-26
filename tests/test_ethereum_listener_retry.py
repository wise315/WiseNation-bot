
import asyncio
from unittest.mock import AsyncMock, Mock, call

import pytest

from app.events.subscribers.ethereum_blocks import (
    EthereumBlockListener,
    EthereumListenerFatalError,
)


def create_listener(**overrides):
    settings = {
        "provider": Mock(),
        "event_engine": Mock(),
        "chain_id": 1,
        "poll_interval": 0.01,
        "max_consecutive_failures": 5,
        "initial_retry_delay": 2.0,
        "max_retry_delay": 30.0,
    }

    settings.update(overrides)

    return EthereumBlockListener(**settings)


@pytest.mark.parametrize(
    "invalid_value",
    [0, -1, True, 1.5],
)
def test_rejects_invalid_failure_limit(invalid_value):
    with pytest.raises(
        ValueError,
        match="max_consecutive_failures",
    ):
        create_listener(
            max_consecutive_failures=invalid_value,
        )


@pytest.mark.parametrize(
    "invalid_value",
    [0, -1, float("inf"), float("nan")],
)
def test_rejects_invalid_initial_retry_delay(invalid_value):
    with pytest.raises(
        ValueError,
        match="initial_retry_delay",
    ):
        create_listener(
            initial_retry_delay=invalid_value,
        )


@pytest.mark.parametrize(
    "invalid_value",
    [0, -1, 1, float("inf"), float("nan")],
)
def test_rejects_invalid_max_retry_delay(invalid_value):
    with pytest.raises(
        ValueError,
        match="max_retry_delay",
    ):
        create_listener(
            max_retry_delay=invalid_value,
        )


@pytest.mark.asyncio
async def test_listener_raises_after_retry_exhaustion():
    listener = create_listener(
        max_consecutive_failures=3,
    )

    original_error = ConnectionError(
        "Ethereum RPC unavailable."
    )

    listener.poll_once = AsyncMock(
        side_effect=original_error,
    )

    listener._wait_or_stop = AsyncMock()

    with pytest.raises(
        EthereumListenerFatalError,
        match="3 consecutive",
    ) as exc_info:
        await asyncio.wait_for(
            listener.run(),
            timeout=2,
        )

    assert exc_info.value.__cause__ is original_error

    assert listener.poll_once.await_count == 3

    assert listener._wait_or_stop.await_count == 2

    assert listener.consecutive_failures == 3

    assert listener.is_running is False


@pytest.mark.asyncio
async def test_listener_uses_exponential_backoff():
    listener = create_listener(
        max_consecutive_failures=5,
        initial_retry_delay=2,
        max_retry_delay=30,
    )

    listener.poll_once = AsyncMock(
        side_effect=ConnectionError("RPC unavailable."),
    )

    listener._wait_or_stop = AsyncMock()

    with pytest.raises(EthereumListenerFatalError):
        await asyncio.wait_for(
            listener.run(),
            timeout=2,
        )

    assert listener._wait_or_stop.await_args_list == [
        call(2),
        call(4),
        call(8),
        call(16),
    ]


@pytest.mark.asyncio
async def test_listener_caps_retry_delay():
    listener = create_listener(
        max_consecutive_failures=6,
        initial_retry_delay=2,
        max_retry_delay=5,
    )

    listener.poll_once = AsyncMock(
        side_effect=ConnectionError("RPC unavailable."),
    )

    listener._wait_or_stop = AsyncMock()

    with pytest.raises(EthereumListenerFatalError):
        await asyncio.wait_for(
            listener.run(),
            timeout=2,
        )

    assert listener._wait_or_stop.await_args_list == [
        call(2),
        call(4),
        call(5),
        call(5),
        call(5),
    ]


@pytest.mark.asyncio
async def test_listener_resets_failure_count_after_success():
    listener = create_listener(
        max_consecutive_failures=3,
    )

    listener.poll_once = AsyncMock(
        side_effect=[
            ConnectionError("First failure."),
            ConnectionError("Second failure."),
            0,
            ConnectionError("New failure."),
            ConnectionError("Another failure."),
            ConnectionError("Final failure."),
        ]
    )

    listener._wait_or_stop = AsyncMock()

    with pytest.raises(EthereumListenerFatalError):
        await asyncio.wait_for(
            listener.run(),
            timeout=2,
        )

    assert listener.poll_once.await_count == 6

    assert listener._wait_or_stop.await_args_list == [
        call(2),
        call(4),
        call(listener.poll_interval),
        call(2),
        call(4),
    ]

    assert listener.consecutive_failures == 3


@pytest.mark.asyncio
async def test_listener_recovers_from_temporary_failure():
    listener = create_listener()

    attempts = 0

    async def poll():
        nonlocal attempts

        attempts += 1

        if attempts == 1:
            raise ConnectionError("Temporary failure.")

        listener.stop()

        return 1

    listener.poll_once = AsyncMock(
        side_effect=poll,
    )

    listener._wait_or_stop = AsyncMock()

    await asyncio.wait_for(
        listener.run(),
        timeout=2,
    )

    assert attempts == 2

    assert listener.consecutive_failures == 0

    assert listener.is_running is False


@pytest.mark.asyncio
async def test_stop_interrupts_retry_delay():
    listener = create_listener(
        initial_retry_delay=30,
        max_retry_delay=30,
    )

    failure_observed = asyncio.Event()

    async def poll():
        failure_observed.set()

        raise ConnectionError("RPC unavailable.")

    listener.poll_once = AsyncMock(
        side_effect=poll,
    )

    task = asyncio.create_task(listener.run())

    try:
        await asyncio.wait_for(
            failure_observed.wait(),
            timeout=1,
        )

        listener.stop()

        await asyncio.wait_for(
            task,
            timeout=1,
        )

        assert listener.poll_once.await_count == 1
        assert listener.is_running is False

    finally:
        listener.stop()

        if not task.done():
            task.cancel()

        await asyncio.gather(
            task,
            return_exceptions=True,
        )


@pytest.mark.asyncio
async def test_listener_propagates_cancellation():
    listener = create_listener()

    polling_started = asyncio.Event()

    async def poll():
        polling_started.set()

        await asyncio.Event().wait()

    listener.poll_once = AsyncMock(
        side_effect=poll,
    )

    listener._wait_or_stop = AsyncMock()

    task = asyncio.create_task(listener.run())

    try:
        await asyncio.wait_for(
            polling_started.wait(),
            timeout=1,
        )

        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        assert listener.consecutive_failures == 0

        listener._wait_or_stop.assert_not_awaited()

        assert listener.is_running is False

    finally:
        if not task.done():
            task.cancel()

        await asyncio.gather(
            task,
            return_exceptions=True,
        )
