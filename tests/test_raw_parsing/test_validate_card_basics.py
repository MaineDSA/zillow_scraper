import re

import pytest
from bs4 import BeautifulSoup, Tag

from src.exceptions import ZillowParseError
from src.scraper import ZillowCardParser


def create_mock_card(address: str | None, link: str | None) -> Tag:
    """Create a mock HTML card for testing."""
    address_html = f"<address>{address}</address>" if address is not None else ""
    link_html = f'<a class="property-card-link" data-test="property-card-link" href="{link}">Link</a>' if link is not None else ""

    html = f"""
        <article data-test="property-card">
                {address_html}
                {link_html}
        </article>
    """

    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("article")
    assert isinstance(card, Tag)
    return card


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
    card = create_mock_card(address, link)

    with pytest.raises(ZillowParseError, match=re.escape(expected_error)):
        ZillowCardParser(card)


@pytest.mark.parametrize(
    ("address", "link"),
    [
        ("123 Main St", "https://www.zillow.com/property/123"),
        ("  123 Main St  ", "https://www.zillow.com/property/123"),
        ("123 Main St", "  https://www.zillow.com/property/123  "),
        ("Café Street 123", "https://www.zillow.com/property/123"),
        ("123 Main St #@$%", "https://www.zillow.com/property/123?param=value"),
        ("A" * 100, "https://www.zillow.com/" + "B" * 100),
    ],
)
def test_valid_inputs(address: str, link: str) -> None:
    """Test various valid input combinations."""
    card = create_mock_card(address, link)

    # Should not raise any exception
    parser = ZillowCardParser(card)
    assert parser.address.strip() == (address.strip() if address else "")
    assert parser.main_link.strip() == (link.strip() if link else "")


def test_address_with_pipe_removal() -> None:
    """Test that pipe characters are removed from addresses."""
    card = create_mock_card("123 Main St | City", "https://www.zillow.com/property/123")
    parser = ZillowCardParser(card)
    assert parser.address == "123 Main St  City"


def test_relative_link_conversion() -> None:
    """Test that relative links are converted to absolute URLs."""
    card = create_mock_card("123 Main St", "/homedetails/123-main-st/123_zpid/")
    parser = ZillowCardParser(card)
    assert parser.main_link == "https://www.zillow.com/homedetails/123-main-st/123_zpid/"


def test_absolute_link_unchanged() -> None:
    """Test that absolute links remain unchanged."""
    absolute_url = "https://www.zillow.com/property/123"
    card = create_mock_card("123 Main St", absolute_url)
    parser = ZillowCardParser(card)
    assert parser.main_link == absolute_url


def test_missing_address_element() -> None:
    """Test handling when address element is missing."""
    html = """
<article data-test="property-card">
<a class="property-card-link" data-test="property-card-link" href="valid_link">Link</a>
</article>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("article")
    assert isinstance(card, Tag)

    with pytest.raises(ZillowParseError, match=re.escape("Missing Address in card.")):
        ZillowCardParser(card)


def test_missing_link_element() -> None:
    """Test handling when link element is missing."""
    html = """
        <article data-test="property-card">
            <address>123 Main St</address>
        </article>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("article")
    assert isinstance(card, Tag)

    with pytest.raises(ZillowParseError, match=re.escape("Missing Link in card.")):
        ZillowCardParser(card)
