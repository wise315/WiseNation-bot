from app.blockchain.address import (
    is_valid_ethereum_address,
    normalize_ethereum_address,
)


def test_valid_ethereum_address():
    address = "0x0000000000000000000000000000000000000001"

    assert is_valid_ethereum_address(address) is True


def test_invalid_ethereum_address():
    address = "0x12345"

    assert is_valid_ethereum_address(address) is False


def test_normalize_ethereum_address():
    address = "0x0000000000000000000000000000000000000001"

    normalized = normalize_ethereum_address(address)

    assert normalized == address


def test_normalize_invalid_address_raises():
    address = "not-a-wallet"

    try:
        normalize_ethereum_address(address)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError for invalid Ethereum address"
        )