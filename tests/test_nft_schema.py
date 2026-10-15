from app.schemas.nft import WalletNFT


def test_wallet_nft_schema():
    nft = WalletNFT(
        contract_address=(
            "0x1234567890abcdef1234567890abcdef12345678"
        ),
        token_id="123",
        collection_name="Test Collection",
        name="Test NFT #123",
        image_url="https://example.com/nft.png",
        token_standard="ERC-721",
        wallet_address=(
            "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        ),
    )

    assert (
        nft.contract_address
        == "0x1234567890abcdef1234567890abcdef12345678"
    )
    assert nft.token_id == "123"
    assert nft.collection_name == "Test Collection"
    assert nft.name == "Test NFT #123"
    assert nft.image_url == "https://example.com/nft.png"
    assert nft.token_standard == "ERC-721"
    assert (
        nft.wallet_address
        == "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
    )


def test_wallet_nft_optional_metadata():
    nft = WalletNFT(
        contract_address=(
            "0x1234567890abcdef1234567890abcdef12345678"
        ),
        token_id="456",
        token_standard="ERC-721",
        wallet_address=(
            "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        ),
    )

    assert nft.collection_name is None
    assert nft.name is None
    assert nft.image_url is None