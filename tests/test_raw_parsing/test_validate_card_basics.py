import re

import pytest

from src.exceptions import ZillowParseError
from src.scraper import _validate_card_basics


@pytest.mark.parametrize(
    ("address", "link", "expected_error"),
    [
        ("", "valid_link", "Missing Address in card."),
        ("valid_address", "", "Missing Link in card."),
        ("", "", "Missing Address, Link in card."),
        (None, "valid_link", "Missing Address in card."),
        ("valid_address", None, "Missing Link in card."),
        (None, None, "Missing Address, Link in card."),
        ("   ", "valid_link", "Missing Address in card."),
        ("valid_address", "   ", "Missing Link in card."),
        ("   ", "   ", "Missing Address, Link in card."),
    ],
)
def test_invalid_inputs(address: str, link: str, expected_error: str) -> None:
    """Test various invalid input combinations."""
    with pytest.raises(ZillowParseError, match=re.escape(expected_error)):
        _validate_card_basics(address, link)


@pytest.mark.parametrize(
    ("address", "link"),
    [
        ("123 Main St", "https://zillow.com/property/123"),
        ("  123 Main St  ", "https://zillow.com/property/123"),
        ("123 Main St", "  https://zillow.com/property/123  "),
        ("Café Street 123", "https://zillow.com/property/123"),
        ("123 Main St #@$%", "https://zillow.com/property/123?param=value"),
        ("A" * 100, "https://zillow.com/" + "B" * 100),
    ],
)
def test_valid_inputs(address: str, link: str) -> None:
    """Test various valid input combinations."""
    # Should not raise any exception
    _validate_card_basics(address, link)
