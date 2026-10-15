from app.blockchain.tokens import DAI, SUPPORTED_TOKENS, USDC


def test_usdc_configuration():
    assert USDC.symbol == "USDC"
    assert USDC.address == "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"


def test_dai_configuration():
    assert DAI.symbol == "DAI"
    assert DAI.address == "0x6B175474E89094C44Da98b954EedeAC495271d0F"


def test_supported_tokens():
    assert len(SUPPORTED_TOKENS) == 2
    assert SUPPORTED_TOKENS[0] == USDC
    assert SUPPORTED_TOKENS[1] == DAI