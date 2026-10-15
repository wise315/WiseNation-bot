from app.blockchain.providers.nft import NFTProvider


def test_nft_provider_is_abstract():
    assert NFTProvider.__abstractmethods__ == {"get_nfts"}


def test_nft_provider_cannot_be_instantiated():
    try:
        NFTProvider()
        assert False, "NFTProvider should not be instantiable"
    except TypeError:
        pass
    