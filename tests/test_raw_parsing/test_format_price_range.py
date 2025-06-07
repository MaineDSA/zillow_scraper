from src.scraper import _clean_price_text, _extract_numeric_price, _format_price_range


def test_format_price_range_empty_list() -> None:
    """Test _format_price_range with empty list."""
    result = _format_price_range([])
    assert result == ""


def test_format_price_range_single_price() -> None:
    """Test _format_price_range with single price."""
    result = _format_price_range(["$2,500"])
    assert result == "$2,500"


def test_format_price_range_identical_prices() -> None:
    """Test _format_price_range with identical price values."""
    result = _format_price_range(["$2,500", "$2500", "$2,500.00"])
    assert result == "$2,500"  # Should return first price when values are same


def test_format_price_range_different_prices() -> None:
    """Test _format_price_range with different prices."""
    result = _format_price_range(["$2,500", "$3,000", "$2,750"])
    assert result == "$2,500 - $3,000"  # Should show min - max


def test_format_price_range_unsorted_prices() -> None:
    """Test _format_price_range sorts prices correctly."""
    result = _format_price_range(["$3,500", "$2,000", "$4,000", "$2,500"])
    assert result == "$2,000 - $4,000"


def test_format_price_range_invalid_prices() -> None:
    """Test _format_price_range with invalid/unparseable prices."""
    result = _format_price_range(["Invalid", "Not a price", "$2,500"])
    assert result == "$2,500"  # Should return valid price when others invalid


def test_format_price_range_all_invalid_prices() -> None:
    """Test _format_price_range with all invalid prices."""
    result = _format_price_range(["Invalid", "Not a price", "ABC"])
    assert result == "Invalid"  # Should return first price as fallback


def test_format_price_range_mixed_formats() -> None:
    """Test _format_price_range with different price formats."""
    result = _format_price_range(["$2,500/mo", "$3000", "$2,750 per month"])
    assert result == "$2,500/mo - $3000"


def test_extract_numeric_price_valid_prices() -> None:
    """Test _extract_numeric_price with valid price strings."""
    assert _extract_numeric_price("$2,500") == 2500
    assert _extract_numeric_price("$3,000.50") == 3000
    assert _extract_numeric_price("2500") == 2500
    assert _extract_numeric_price("$1,234,567") == 1234567


def test_extract_numeric_price_invalid_prices() -> None:
    """Test _extract_numeric_price with invalid price strings."""
    assert _extract_numeric_price("Invalid") == 0
    assert _extract_numeric_price("Not a price") == 0
    assert _extract_numeric_price("") == 0
    assert _extract_numeric_price("$") == 0


def test_extract_numeric_price_edge_cases() -> None:
    """Test _extract_numeric_price with edge cases."""
    assert _extract_numeric_price("$2,500/mo + utilities") == 2500
    assert _extract_numeric_price("Price: $3,000 per month") == 3000
    assert _extract_numeric_price("$0") == 0
    assert _extract_numeric_price("$.50") == 0  # Should handle decimal-only


def test_clean_price_text_basic_cleaning() -> None:
    """Test _clean_price_text removes unwanted text."""
    assert _clean_price_text("$2,500/mo + 2 bds") == "$2,500"
    assert _clean_price_text("$3,000 + 3 bd") == "$3,000"
    assert _clean_price_text("$2,750/mo") == "$2,750"


def test_clean_price_text_complex_cleaning() -> None:
    """Test _clean_price_text with complex strings."""
    assert _clean_price_text("$2,500+ 2 bds") == "$2,500"
    assert _clean_price_text("$3,000/mo + 1 bd + utilities") == "$3,000"
    assert _clean_price_text("   $2,750/mo + 3 bds   ") == "$2,750"


def test_clean_price_text_edge_cases() -> None:
    """Test _clean_price_text with edge cases."""
    assert _clean_price_text("") == ""
    assert _clean_price_text("   ") == ""
    assert _clean_price_text("No price here") == "No price here"
    assert _clean_price_text("$2,500+ bd") == "$2,500"  # Edge case with 'bd' without number


def test_price_range_formatting_workflow() -> None:
    """Test the complete workflow from raw prices to formatted range."""
    raw_prices = ["$3,000/mo + 2 bds", "$2,500/mo + 1 bd", "$3,500+ 3 bds", "$2,750/mo + 2 bds"]

    # Clean the prices first
    cleaned_prices = [_clean_price_text(price) for price in raw_prices]
    expected_cleaned = ["$3,000", "$2,500", "$3,500", "$2,750"]
    assert cleaned_prices == expected_cleaned

    # Format as range
    result = _format_price_range(cleaned_prices)
    expected_range = "$2,500 - $3,500"
    assert result == expected_range
