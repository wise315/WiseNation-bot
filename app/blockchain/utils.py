from decimal import Decimal


WEI_PER_ETH = Decimal("1000000000000000000")


def wei_to_eth(wei: int) -> Decimal:
    return Decimal(wei) / WEI_PER_ETH