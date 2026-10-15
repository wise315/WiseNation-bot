from app.schemas.collection import NFTCollection


def test_collection_schema_with_all_fields():
    collection = NFTCollection(
        contract_address="0x1234567890abcdef1234567890abcdef12345678",
        name="Test Collection",
        symbol="TEST",
        description="A test NFT collection.",
        image_url="https://example.com/image.png",
        banner_image_url="https://example.com/banner.png",
        token_standard="ERC721",
        blockchain="ethereum",
    )

    assert (
        collection.contract_address
        == "0x1234567890abcdef1234567890abcdef12345678"
    )
    assert collection.name == "Test Collection"
    assert collection.symbol == "TEST"
    assert collection.description == "A test NFT collection."
    assert collection.image_url == "https://example.com/image.png"
    assert collection.banner_image_url == "https://example.com/banner.png"
    assert collection.token_standard == "ERC721"
    assert collection.blockchain == "ethereum"


def test_collection_schema_with_optional_fields():
    collection = NFTCollection(
        contract_address="0x1234567890abcdef1234567890abcdef12345678",
        name="Test Collection",
        blockchain="ethereum",
    )

    assert collection.name == "Test Collection"
    assert collection.symbol is None
    assert collection.description is None
    assert collection.image_url is None
    assert collection.banner_image_url is None
    assert collection.token_standard is None