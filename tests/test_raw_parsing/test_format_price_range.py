from bs4 import BeautifulSoup, Tag

from src.scraper import ZillowCardParser


def create_test_parser() -> ZillowCardParser:
    """Create a test parser instance with minimal valid data."""
    html = """
<article data-test="property-card">
<address>123 Test St</address>
<a class="property-card-link" data-test="property-card-link" href="/property/123">
Property Link
</a>
</article>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("article")
    assert isinstance(card, Tag)
    return ZillowCardParser(card)


def test_format_price_range_empty_list() -> None:
    """Test _format_price_range with empty list."""
    parser = create_test_parser()
    result = parser._format_price_range([])
    assert not result


def test_format_price_range_single_price() -> None:
    """Test _format_price_range with single price."""
    parser = create_test_parser()
    result = parser._format_price_range(["$2,500"])
    assert result == "$2,500"


def test_format_price_range_identical_prices() -> None:
    """Test _format_price_range with identical price values."""
    parser = create_test_parser()
    result = parser._format_price_range(["$2,500", "$2500", "$2,500.00"])
    assert result == "$2,500"  # Should return first price when values are same


def test_format_price_range_different_prices() -> None:
    """Test _format_price_range with different prices."""
    parser = create_test_parser()
    result = parser._format_price_range(["$2,500", "$3,000", "$2,750"])
    assert result == "$2,500 - $3,000"  # Should show min - max


def test_format_price_range_unsorted_prices() -> None:
    """Test _format_price_range sorts prices correctly."""
    parser = create_test_parser()
    result = parser._format_price_range(["$3,500", "$2,000", "$4,000", "$2,500"])
    assert result == "$2,000 - $4,000"


def test_format_price_range_invalid_prices() -> None:
    """Test _format_price_range with invalid/unparseable prices."""
    parser = create_test_parser()
    result = parser._format_price_range(["Invalid", "Not a price", "$2,500"])
    assert result == "$2,500"  # Should return valid price when others invalid


def test_format_price_range_all_invalid_prices() -> None:
    """Test _format_price_range with all invalid prices."""
    parser = create_test_parser()
    result = parser._format_price_range(["Invalid", "Not a price", "ABC"])
    assert result == "Invalid"  # Should return first price as fallback


def test_format_price_range_mixed_formats() -> None:
    """Test _format_price_range with different price formats."""
    parser = create_test_parser()
    result = parser._format_price_range(["$2,500/mo", "$3000", "$2,750 per month"])
    assert result == "$2,500/mo - $3000"


def test_extract_numeric_price_valid_prices() -> None:
    """Test _extract_numeric_price with valid price strings."""
    parser = create_test_parser()
    expected_numeric_price = 2500
    assert parser._extract_numeric_price("$2,500") == expected_numeric_price
    expected_numeric_price = 3000
    assert parser._extract_numeric_price("$3,000.50") == expected_numeric_price
    expected_numeric_price = 2500
    assert parser._extract_numeric_price("2500") == expected_numeric_price
    expected_numeric_price = 1234567
    assert parser._extract_numeric_price("$1,234,567") == expected_numeric_price


def test_extract_numeric_price_invalid_prices() -> None:
    """Test _extract_numeric_price with invalid price strings."""
    parser = create_test_parser()
    expected_numeric_price = 0
    assert parser._extract_numeric_price("Invalid") == expected_numeric_price
    assert parser._extract_numeric_price("Not a price") == expected_numeric_price
    assert parser._extract_numeric_price("") == expected_numeric_price
    assert parser._extract_numeric_price("$") == expected_numeric_price


def test_extract_numeric_price_edge_cases() -> None:
    """Test _extract_numeric_price with edge cases."""
    parser = create_test_parser()
    expected_numeric_price = 2500
    assert parser._extract_numeric_price("$2,500/mo + utilities") == expected_numeric_price
    expected_numeric_price = 3000
    assert parser._extract_numeric_price("Price: $3,000 per month") == expected_numeric_price
    expected_numeric_price = 0
    assert parser._extract_numeric_price("$0") == expected_numeric_price
    assert parser._extract_numeric_price("$.50") == expected_numeric_price  # Should handle decimal-only


def test_clean_price_text_basic_cleaning() -> None:
    """Test _clean_price_text removes unwanted text."""
    parser = create_test_parser()
    assert parser._clean_price_text("$2,500/mo + 2 bds") == "$2,500"
    assert parser._clean_price_text("$3,000 + 3 bd") == "$3,000"
    assert parser._clean_price_text("$2,750/mo") == "$2,750"


def test_clean_price_text_complex_cleaning() -> None:
    """Test _clean_price_text with complex strings."""
    parser = create_test_parser()
    assert parser._clean_price_text("$2,500+ 2 bds") == "$2,500"
    assert parser._clean_price_text("$3,000/mo + 1 bd + utilities") == "$3,000"
    assert parser._clean_price_text("   $2,750/mo + 3 bds   ") == "$2,750"


def test_clean_price_text_edge_cases() -> None:
    """Test _clean_price_text with edge cases."""
    parser = create_test_parser()
    assert not parser._clean_price_text("")
    assert not parser._clean_price_text("   ")
    assert parser._clean_price_text("No price here") == "No price here"
    assert parser._clean_price_text("$2,500+ bd") == "$2,500"  # Edge case with 'bd' without number


def test_price_range_formatting_workflow() -> None:
    """Test the complete workflow from raw prices to formatted range."""
    parser = create_test_parser()
    raw_prices = ["$3,000/mo + 2 bds", "$2,500/mo + 1 bd", "$3,500+ 3 bds", "$2,750/mo + 2 bds"]

    # Clean the prices first
    cleaned_prices = [parser._clean_price_text(price) for price in raw_prices]
    expected_cleaned = ["$3,000", "$2,500", "$3,500", "$2,750"]
    assert cleaned_prices == expected_cleaned

    # Format as range
    result = parser._format_price_range(cleaned_prices)
    expected_range = "$2,500 - $3,500"
    assert result == expected_range


def test_price_cleanup_patterns() -> None:
    """Test that price cleanup patterns work correctly."""
    parser = create_test_parser()

    # Test bedroom removal patterns
    assert parser._clean_price_text("$2,500 + 2 bds") == "$2,500"
    assert parser._clean_price_text("$2,500+ 3 bd") == "$2,500"
    assert parser._clean_price_text("$2,500 1 bd") == "$2,500"

    # Test utility removal
    assert parser._clean_price_text("$2,500 utilities") == "$2,500"

    # Test /mo removal
    assert parser._clean_price_text("$2,500/mo") == "$2,500"

    # Test + removal
    assert parser._clean_price_text("$2,500+") == "$2,500"

    # Test whitespace normalization
    assert parser._clean_price_text("$2,500   +    2   bds") == "$2,500"


def test_price_cleanup_constants() -> None:
    """Test that the price cleanup constants are working."""
    parser = create_test_parser()

    # Verify the constants exist and work
    assert hasattr(parser, "PRICE_CLEANUP_PATTERNS")
    assert hasattr(parser, "PRICE_REPLACEMENTS")

    # Test each replacement string
    for replacement in parser.PRICE_REPLACEMENTS:
        test_string = f"$2,500{replacement}"
        result = parser._clean_price_text(test_string)
        assert replacement not in result

    # Test that patterns are applied correctly
    test_cases = [
        ("$2,500 + 2 bds", "$2,500"),
        ("$2,500+ 1 bd", "$2,500"),
        ("$2,500  +  3  bds", "$2,500"),
    ]

    for input_str, expected in test_cases:
        result = parser._clean_price_text(input_str)
        assert result == expected


def test_numeric_price_extraction_edge_cases() -> None:
    """Test numeric price extraction with various edge cases."""
    parser = create_test_parser()

    # Test with commas and periods
    expected_numeric_price = 1234
    assert parser._extract_numeric_price("$1,234.56") == expected_numeric_price
    expected_numeric_price = 1234567
    assert parser._extract_numeric_price("$1,234,567.89") == expected_numeric_price

    # Test with no currency symbol
    expected_numeric_price = 2500
    assert parser._extract_numeric_price("2500") == expected_numeric_price
    assert parser._extract_numeric_price("2,500") == expected_numeric_price

    # Test with extra text
    expected_numeric_price = 2500
    assert parser._extract_numeric_price("Rent: $2,500 per month") == expected_numeric_price
    assert parser._extract_numeric_price("$2,500 (includes utilities)") == expected_numeric_price
