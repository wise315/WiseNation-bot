from decimal import Decimal

from app.blockchain.utils import wei_to_eth


def test_wei_to_eth():
    assert wei_to_eth(0) == Decimal("0")
    assert wei_to_eth(1_000_000_000_000_000_000) == Decimal("1")
    assert wei_to_eth(250_000_000_000_000_000) == Decimal("0.25")