
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import run as runtime

from app.events.subscribers.ethereum_blocks import (
    EthereumListenerFatalError,
)


@pytest.fixture
def runtime_dependencies(monkeypatch):
    lifecycle = []

    # Application settings
    settings = SimpleNamespace(
        telegram_bot_token="test-token",
        app_env="testing",
    )

    monkeypatch.setattr(
        runtime,
        "get_settings",
        Mock(return_value=settings),
    )

    # Telegram bot
    bot = Mock()

    async def close_bot_session():
        lifecycle.append("bot_session_closed")

    bot.session.close = AsyncMock(
        side_effect=close_bot_session,
    )

    create_bot = Mock(return_value=bot)

    monkeypatch.setattr(
        runtime,
        "create_bot",
        create_bot,
    )

    # Telegram dispatcher
    dispatcher = Mock()
    dispatcher.start_polling = AsyncMock()

    create_dispatcher = Mock(
        return_value=dispatcher,
    )

    monkeypatch.setattr(
        runtime,
        "create_dispatcher",
        create_dispatcher,
    )

    # Blockchain provider
    ethereum = Mock()

    async def close_ethereum():
        lifecycle.append("ethereum_closed")

    ethereum.close = AsyncMock(
        side_effect=close_ethereum,
    )

    blockchain = SimpleNamespace(
        ethereum=ethereum,
    )

    blockchain_factory = Mock(
        return_value=blockchain,
    )

    monkeypatch.setattr(
        runtime,
        "BlockchainService",
        blockchain_factory,
    )

    # Database session
    db_session = Mock()

    async def enter_database():
        lifecycle.append("database_opened")

        return db_session

    async def exit_database(*args):
        lifecycle.append("database_closed")

        return False

    session_context = Mock()

    session_context.__aenter__ = AsyncMock(
        side_effect=enter_database,
    )

    session_context.__aexit__ = AsyncMock(
        side_effect=exit_database,
    )

    session_factory = Mock(
        return_value=session_context,
    )

    monkeypatch.setattr(
        runtime,
        "AsyncSessionLocal",
        session_factory,
    )

    # Checkpoint service
    checkpoint_service = Mock()
    checkpoint_service.session = db_session

    checkpoint_service.get_checkpoint = AsyncMock(
        return_value=SimpleNamespace(
            last_processed_block=12345,
        ),
    )

    checkpoint_factory = Mock(
        return_value=checkpoint_service,
    )

    monkeypatch.setattr(
        runtime,
        "BlockCheckpointService",
        checkpoint_factory,
    )

    # Canonical block service
    canonical_service = Mock()
    canonical_service.session = db_session

    canonical_factory = Mock(
        return_value=canonical_service,
    )

    monkeypatch.setattr(
        runtime,
        "CanonicalBlockService",
        canonical_factory,
    )

    # NFT event persistence service
    nft_event_service = Mock()
    nft_event_service.session = db_session

    nft_event_factory = Mock(
        return_value=nft_event_service,
    )

    monkeypatch.setattr(
        runtime,
        "NFTBlockchainEventService",
        nft_event_factory,
    )

    # Event engine
    event_engine = Mock()

    engine_factory = Mock(
        return_value=event_engine,
    )

    monkeypatch.setattr(
        runtime,
        "EventEngine",
        engine_factory,
    )

    # Activity provider
    activity_provider = Mock()

    activity_factory = Mock(
        return_value=activity_provider,
    )

    monkeypatch.setattr(
        runtime,
        "EthereumActivityProvider",
        activity_factory,
    )

    # NFT decoder
    nft_decoder = Mock()

    decoder_factory = Mock(
        return_value=nft_decoder,
    )

    monkeypatch.setattr(
        runtime,
        "NFTEventDecoder",
        decoder_factory,
    )

    # NFT processor
    nft_processor = Mock()

    processor_factory = Mock(
        return_value=nft_processor,
    )

    monkeypatch.setattr(
        runtime,
        "NFTEventProcessor",
        processor_factory,
    )

    # Block pipeline
    block_pipeline = Mock()

    def start_pipeline():
        lifecycle.append("pipeline_started")

    async def shutdown_pipeline():
        lifecycle.append("pipeline_shutdown")

    block_pipeline.start = Mock(
        side_effect=start_pipeline,
    )

    block_pipeline.shutdown = AsyncMock(
        side_effect=shutdown_pipeline,
    )

    pipeline_factory = Mock(
        return_value=block_pipeline,
    )

    monkeypatch.setattr(
        runtime,
        "BlockEventPipeline",
        pipeline_factory,
    )

    # Ethereum listener
    block_listener = Mock()

    listener_started = asyncio.Event()
    listener_finished = asyncio.Event()

    async def run_listener():
        lifecycle.append("listener_started")

        listener_started.set()

        try:
            await asyncio.Event().wait()

        finally:
            lifecycle.append("listener_finished")

            listener_finished.set()

    def stop_listener():
        lifecycle.append("listener_stop_requested")

    block_listener.run = AsyncMock(
        side_effect=run_listener,
    )

    block_listener.stop = Mock(
        side_effect=stop_listener,
    )

    listener_factory = Mock(
        return_value=block_listener,
    )

    monkeypatch.setattr(
        runtime,
        "EthereumBlockListener",
        listener_factory,
    )

    # Default Telegram polling behavior:
    # wait until the listener starts, then exit normally.
    async def run_polling(*args, **kwargs):
        await listener_started.wait()

        lifecycle.append("polling_finished")

    dispatcher.start_polling.side_effect = run_polling

    return SimpleNamespace(
        lifecycle=lifecycle,
        settings=settings,
        bot=bot,
        create_bot=create_bot,
        dispatcher=dispatcher,
        create_dispatcher=create_dispatcher,
        ethereum=ethereum,
        blockchain=blockchain,
        blockchain_factory=blockchain_factory,
        db_session=db_session,
        session_context=session_context,
        session_factory=session_factory,
        checkpoint_service=checkpoint_service,
        checkpoint_factory=checkpoint_factory,
        canonical_service=canonical_service,
        canonical_factory=canonical_factory,
        nft_event_service=nft_event_service,
        nft_event_factory=nft_event_factory,
        event_engine=event_engine,
        engine_factory=engine_factory,
        activity_provider=activity_provider,
        activity_factory=activity_factory,
        nft_decoder=nft_decoder,
        decoder_factory=decoder_factory,
        nft_processor=nft_processor,
        processor_factory=processor_factory,
        block_pipeline=block_pipeline,
        pipeline_factory=pipeline_factory,
        block_listener=block_listener,
        listener_factory=listener_factory,
        listener_started=listener_started,
        listener_finished=listener_finished,
    )


@pytest.mark.asyncio
async def test_main_initializes_runtime_dependencies(
    runtime_dependencies,
):
    deps = runtime_dependencies

    await asyncio.wait_for(
        runtime.main(),
        timeout=2,
    )

    deps.create_bot.assert_called_once_with(
        "test-token",
    )

    deps.create_dispatcher.assert_called_once_with()

    deps.blockchain_factory.assert_called_once_with()

    deps.session_factory.assert_called_once_with()

    deps.checkpoint_factory.assert_called_once_with(
        deps.db_session,
    )

    deps.canonical_factory.assert_called_once_with(
        session=deps.db_session,
    )

    deps.nft_event_factory.assert_called_once_with(
        session=deps.db_session,
    )

    deps.engine_factory.assert_called_once_with()

    deps.activity_factory.assert_called_once_with(
        deps.ethereum,
    )

    deps.decoder_factory.assert_called_once_with(
        chain_id=1,
    )

    deps.processor_factory.assert_called_once_with(
        decoder=deps.nft_decoder,
        event_engine=deps.event_engine,
    )

    deps.pipeline_factory.assert_called_once_with(
        activity_provider=deps.activity_provider,
        nft_processor=deps.nft_processor,
        event_engine=deps.event_engine,
        chain_id=1,
        checkpoint_service=deps.checkpoint_service,
        canonical_block_service=deps.canonical_service,
        nft_event_service=deps.nft_event_service,
    )

    deps.block_pipeline.start.assert_called_once()

    deps.block_listener.run.assert_awaited_once()

    deps.dispatcher.start_polling.assert_awaited_once_with(
        deps.bot,
    )


@pytest.mark.asyncio
async def test_main_recovers_persisted_checkpoint(
    runtime_dependencies,
):
    deps = runtime_dependencies

    deps.checkpoint_service.get_checkpoint.return_value = (
        SimpleNamespace(
            last_processed_block=19000000,
        )
    )

    await asyncio.wait_for(
        runtime.main(),
        timeout=2,
    )

    deps.checkpoint_service.get_checkpoint.assert_awaited_once_with(
        chain_id=1,
    )

    deps.listener_factory.assert_called_once_with(
        provider=deps.ethereum,
        event_engine=deps.event_engine,
        chain_id=1,
        start_from_block=19000000,
    )


@pytest.mark.asyncio
async def test_main_handles_missing_checkpoint(
    runtime_dependencies,
):
    deps = runtime_dependencies

    deps.checkpoint_service.get_checkpoint.return_value = None

    await asyncio.wait_for(
        runtime.main(),
        timeout=2,
    )

    deps.listener_factory.assert_called_once_with(
        provider=deps.ethereum,
        event_engine=deps.event_engine,
        chain_id=1,
        start_from_block=None,
    )


@pytest.mark.asyncio
async def test_main_starts_pipeline_before_listener(
    runtime_dependencies,
):
    deps = runtime_dependencies

    await asyncio.wait_for(
        runtime.main(),
        timeout=2,
    )

    assert (
        deps.lifecycle.index("pipeline_started")
        < deps.lifecycle.index("listener_started")
    )


@pytest.mark.asyncio
async def test_main_shuts_down_after_normal_polling_exit(
    runtime_dependencies,
):
    deps = runtime_dependencies

    await asyncio.wait_for(
        runtime.main(),
        timeout=2,
    )

    assert deps.listener_finished.is_set()

    deps.block_listener.stop.assert_called_once()

    deps.block_pipeline.shutdown.assert_awaited_once()

    deps.session_context.__aexit__.assert_awaited_once()

    deps.ethereum.close.assert_awaited_once()

    deps.bot.session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_preserves_resource_cleanup_order(
    runtime_dependencies,
):
    deps = runtime_dependencies

    await asyncio.wait_for(
        runtime.main(),
        timeout=2,
    )

    lifecycle = deps.lifecycle

    assert (
        lifecycle.index("listener_finished")
        < lifecycle.index("pipeline_shutdown")
        < lifecycle.index("database_closed")
        < lifecycle.index("ethereum_closed")
        < lifecycle.index("bot_session_closed")
    )


@pytest.mark.asyncio
async def test_main_propagates_fatal_listener_failure(
    runtime_dependencies,
):
    deps = runtime_dependencies

    polling_started = asyncio.Event()
    polling_finished = asyncio.Event()

    fatal_error = EthereumListenerFatalError(
        "Ethereum retry budget exhausted."
    )

    async def run_polling(*args, **kwargs):
        polling_started.set()

        try:
            await asyncio.Event().wait()

        finally:
            polling_finished.set()

    async def run_listener():
        await polling_started.wait()

        raise fatal_error

    deps.dispatcher.start_polling.side_effect = run_polling

    deps.block_listener.run.side_effect = run_listener

    with pytest.raises(
        EthereumListenerFatalError,
    ) as exc_info:
        await asyncio.wait_for(
            runtime.main(),
            timeout=2,
        )

    assert exc_info.value is fatal_error

    assert polling_finished.is_set()

    deps.block_listener.stop.assert_called_once()

    deps.block_pipeline.shutdown.assert_awaited_once()

    deps.session_context.__aexit__.assert_awaited_once()

    deps.ethereum.close.assert_awaited_once()

    deps.bot.session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_propagates_telegram_polling_failure(
    runtime_dependencies,
):
    deps = runtime_dependencies

    polling_error = RuntimeError(
        "Telegram polling failed."
    )

    async def run_polling(*args, **kwargs):
        await deps.listener_started.wait()

        raise polling_error

    deps.dispatcher.start_polling.side_effect = run_polling

    with pytest.raises(
        RuntimeError,
        match="Telegram polling failed",
    ) as exc_info:
        await asyncio.wait_for(
            runtime.main(),
            timeout=2,
        )

    assert exc_info.value is polling_error

    assert deps.listener_finished.is_set()

    deps.block_listener.stop.assert_called_once()

    deps.block_pipeline.shutdown.assert_awaited_once()

    deps.ethereum.close.assert_awaited_once()

    deps.bot.session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_closes_bot_when_ethereum_cleanup_fails(
    runtime_dependencies,
):
    deps = runtime_dependencies

    deps.ethereum.close.side_effect = RuntimeError(
        "Ethereum cleanup failed."
    )

    with pytest.raises(
        RuntimeError,
        match="Ethereum cleanup failed",
    ):
        await asyncio.wait_for(
            runtime.main(),
            timeout=2,
        )

    deps.block_pipeline.shutdown.assert_awaited_once()

    deps.session_context.__aexit__.assert_awaited_once()

    deps.ethereum.close.assert_awaited_once()

    deps.bot.session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_closes_bot_when_dispatcher_creation_fails(
    runtime_dependencies,
):
    deps = runtime_dependencies

    startup_error = RuntimeError(
        "Dispatcher initialization failed."
    )

    deps.create_dispatcher.side_effect = startup_error

    with pytest.raises(RuntimeError) as exc_info:
        await asyncio.wait_for(
            runtime.main(),
            timeout=2,
        )

    assert exc_info.value is startup_error

    deps.bot.session.close.assert_awaited_once()

    deps.blockchain_factory.assert_not_called()

    deps.session_factory.assert_not_called()


@pytest.mark.asyncio
async def test_main_closes_bot_when_blockchain_creation_fails(
    runtime_dependencies,
):
    deps = runtime_dependencies

    startup_error = RuntimeError(
        "Blockchain initialization failed."
    )

    deps.blockchain_factory.side_effect = startup_error

    with pytest.raises(RuntimeError) as exc_info:
        await asyncio.wait_for(
            runtime.main(),
            timeout=2,
        )

    assert exc_info.value is startup_error

    deps.bot.session.close.assert_awaited_once()

    deps.session_factory.assert_not_called()


@pytest.mark.asyncio
async def test_main_closes_resources_when_database_entry_fails(
    runtime_dependencies,
):
    deps = runtime_dependencies

    startup_error = RuntimeError(
        "Database connection failed."
    )

    deps.session_context.__aenter__.side_effect = (
        startup_error
    )

    with pytest.raises(RuntimeError) as exc_info:
        await asyncio.wait_for(
            runtime.main(),
            timeout=2,
        )

    assert exc_info.value is startup_error

    deps.session_context.__aexit__.assert_not_awaited()

    deps.ethereum.close.assert_awaited_once()

    deps.bot.session.close.assert_awaited_once()

    deps.pipeline_factory.assert_not_called()


@pytest.mark.asyncio
async def test_main_closes_resources_when_checkpoint_recovery_fails(
    runtime_dependencies,
):
    deps = runtime_dependencies

    startup_error = RuntimeError(
        "Checkpoint recovery failed."
    )

    deps.checkpoint_service.get_checkpoint.side_effect = (
        startup_error
    )

    with pytest.raises(RuntimeError) as exc_info:
        await asyncio.wait_for(
            runtime.main(),
            timeout=2,
        )

    assert exc_info.value is startup_error

    deps.session_context.__aexit__.assert_awaited_once()

    deps.ethereum.close.assert_awaited_once()

    deps.bot.session.close.assert_awaited_once()

    deps.pipeline_factory.assert_not_called()


@pytest.mark.asyncio
async def test_main_drains_pipeline_when_pipeline_start_fails(
    runtime_dependencies,
):
    deps = runtime_dependencies

    startup_error = RuntimeError(
        "Pipeline startup failed."
    )

    def fail_pipeline_start():
        deps.lifecycle.append("pipeline_started")

        raise startup_error

    deps.block_pipeline.start.side_effect = (
        fail_pipeline_start
    )

    with pytest.raises(RuntimeError) as exc_info:
        await asyncio.wait_for(
            runtime.main(),
            timeout=2,
        )

    assert exc_info.value is startup_error

    deps.block_pipeline.shutdown.assert_awaited_once()

    deps.listener_factory.assert_not_called()

    deps.session_context.__aexit__.assert_awaited_once()

    deps.ethereum.close.assert_awaited_once()

    deps.bot.session.close.assert_awaited_once()

    assert (
        deps.lifecycle.index("pipeline_shutdown")
        < deps.lifecycle.index("database_closed")
    )


@pytest.mark.asyncio
async def test_main_drains_pipeline_when_listener_creation_fails(
    runtime_dependencies,
):
    deps = runtime_dependencies

    startup_error = RuntimeError(
        "Listener initialization failed."
    )

    deps.listener_factory.side_effect = startup_error

    with pytest.raises(RuntimeError) as exc_info:
        await asyncio.wait_for(
            runtime.main(),
            timeout=2,
        )

    assert exc_info.value is startup_error

    deps.block_pipeline.start.assert_called_once()

    deps.block_pipeline.shutdown.assert_awaited_once()

    deps.block_listener.run.assert_not_awaited()

    deps.dispatcher.start_polling.assert_not_awaited()

    deps.session_context.__aexit__.assert_awaited_once()

    deps.ethereum.close.assert_awaited_once()

    deps.bot.session.close.assert_awaited_once()

    assert (
        deps.lifecycle.index("pipeline_shutdown")
        < deps.lifecycle.index("database_closed")
        < deps.lifecycle.index("ethereum_closed")
        < deps.lifecycle.index("bot_session_closed")
    )
