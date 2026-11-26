
from unittest.mock import Mock

from app.events.processors.block_pipeline import BlockEventPipeline


def test_runtime_services_share_database_session():
    shared_session = object()

    checkpoint_service = Mock()
    checkpoint_service.session = shared_session

    canonical_service = Mock()
    canonical_service.session = shared_session

    nft_event_service = Mock()
    nft_event_service.session = shared_session

    pipeline = BlockEventPipeline(
        activity_provider=Mock(),
        nft_processor=Mock(),
        event_engine=Mock(),
        chain_id=1,
        checkpoint_service=checkpoint_service,
        canonical_block_service=canonical_service,
        nft_event_service=nft_event_service,
    )

    assert pipeline.checkpoint_service.session is shared_session
    assert pipeline.canonical_block_service.session is shared_session
    assert pipeline.nft_event_service.session is shared_session
