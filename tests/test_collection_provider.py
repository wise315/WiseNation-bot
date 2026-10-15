import pytest

from app.blockchain.providers.collection import CollectionProvider


def test_collection_provider_is_abstract():
    assert CollectionProvider.__abstractmethods__ == {
        "get_collection",
        "search_collections",
    }


def test_collection_provider_cannot_be_instantiated():
    with pytest.raises(TypeError):
        CollectionProvider()