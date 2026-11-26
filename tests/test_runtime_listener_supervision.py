
import asyncio

import pytest

from run import supervise_runtime


@pytest.mark.asyncio
async def test_runtime_stops_when_listener_fails():
    async def polling():
        await asyncio.Event().wait()

    async def listener():
        raise RuntimeError("Listener crashed")

    polling_task = asyncio.create_task(polling())
    listener_task = asyncio.create_task(listener())

    with pytest.raises(
        RuntimeError,
        match="Listener crashed",
    ):
        await supervise_runtime(
            polling_task,
            listener_task,
        )

    assert polling_task.done()
    assert listener_task.done()


@pytest.mark.asyncio
async def test_runtime_stops_listener_when_polling_finishes():
    stopped = asyncio.Event()

    async def polling():
        return None

    async def listener():
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    polling_task = asyncio.create_task(polling())
    listener_task = asyncio.create_task(listener())

    await supervise_runtime(
        polling_task,
        listener_task,
    )

    assert stopped.is_set()
    assert polling_task.done()
    assert listener_task.done()


@pytest.mark.asyncio
async def test_runtime_detects_unexpected_listener_exit():
    async def polling():
        await asyncio.Event().wait()

    async def listener():
        return None

    polling_task = asyncio.create_task(polling())
    listener_task = asyncio.create_task(listener())

    with pytest.raises(
        RuntimeError,
        match="Ethereum block listener stopped unexpectedly",
    ):
        await supervise_runtime(
            polling_task,
            listener_task,
        )

    assert polling_task.done()
    assert listener_task.done()
