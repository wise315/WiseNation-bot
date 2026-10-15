from web3 import Web3


def is_valid_ethereum_address(address: str) -> bool:
    normalized_address = address.strip()

    return Web3.is_address(normalized_address)


def normalize_ethereum_address(address: str) -> str:
    normalized_address = address.strip()

    if not Web3.is_address(normalized_address):
        raise ValueError("Invalid Ethereum address.")

    return Web3.to_checksum_address(normalized_address)