import re

import pytest
from bs4 import BeautifulSoup, Tag

from src.exceptions import ZillowParseError
from src.scraper import ZillowCardParser


def create_test_card(link_html: str = "", address: str = "123 Test St") -> Tag:
    """Create a test card with specified link HTML and a valid address."""
    html = f"""
        <article data-test="property-card">
            <address>{address}</address>
            {link_html}
        </article>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("article")
    assert isinstance(card, Tag)
    return card


def test_valid_absolute_url() -> None:
    """Test with valid absolute URL."""
    link_html = """
        <a class="property-card-link" data-test="property-card-link" href="https://www.zillow.com/property/123">
            Property Link
        </a>
    """
    card = create_test_card(link_html)
    parser = ZillowCardParser(card)

    assert parser.main_link == "https://www.zillow.com/property/123"


def test_valid_relative_url() -> None:
    """Test with valid relative URL."""
    link_html = """
        <a class="property-card-link" data-test="property-card-link" href="/property/456">
            Property Link
        </a>
    """
    card = create_test_card(link_html)
    parser = ZillowCardParser(card)

    assert parser.main_link == "https://www.zillow.com/property/456"


def test_no_link_element_found() -> None:
    """Test when no matching link element is found."""
    link_html = """
        <a class="different-class" href="/property/123">
            Not the right link
        </a>
        <span>Some other content</span>
    """
    card = create_test_card(link_html)

    # This should raise a ZillowParseError due to missing valid link
    with pytest.raises(ZillowParseError, match=re.escape("Missing Link in card.")):
        ZillowCardParser(card)


def test_link_element_is_none() -> None:
    """Test when find() returns None (no link element)."""
    # Card with no link element at all
    card = create_test_card("")

    # This should raise a ZillowParseError due to missing link
    with pytest.raises(ZillowParseError, match=re.escape("Missing Link in card.")):
        ZillowCardParser(card)


def test_wrong_class_name() -> None:
    """Test with link that has wrong class name."""
    link_html = """
        <a class="wrong-class" data-test="property-card-link" href="/property/123">
            Property Link
        </a>
    """
    card = create_test_card(link_html)

    # This should raise a ZillowParseError due to missing valid link
    with pytest.raises(ZillowParseError, match=re.escape("Missing Link in card.")):
        ZillowCardParser(card)


def test_wrong_data_test_attribute() -> None:
    """Test with link that has wrong data-test attribute."""
    link_html = """
        <a class="property-card-link" data-test="wrong-test" href="/property/123">
            Property Link
        </a>
    """
    card = create_test_card(link_html)

    # This should raise a ZillowParseError due to missing valid link
    with pytest.raises(ZillowParseError, match=re.escape("Missing Link in card.")):
        ZillowCardParser(card)


def test_missing_data_test_attribute() -> None:
    """Test with link that's missing data-test attribute."""
    link_html = """
        <a class="property-card-link" href="/property/123">
            Property Link
        </a>
    """
    card = create_test_card(link_html)

    # This should raise a ZillowParseError due to missing valid link
    with pytest.raises(ZillowParseError, match=re.escape("Missing Link in card.")):
        ZillowCardParser(card)


def test_href_is_none() -> None:
    """Test when href attribute is None."""
    link_html = """
        <a class="property-card-link" data-test="property-card-link">
            Property Link (no href)
        </a>
    """
    card = create_test_card(link_html)

    # This should raise a ZillowParseError due to missing valid link
    with pytest.raises(ZillowParseError, match=re.escape("Missing Link in card.")):
        ZillowCardParser(card)


def test_href_is_empty_string() -> None:
    """Test when href attribute is empty string."""
    link_html = """
        <a class="property-card-link" data-test="property-card-link" href="">
            Property Link
        </a>
    """
    card = create_test_card(link_html)

    # This should raise a ZillowParseError due to missing valid link (empty href)
    with pytest.raises(ZillowParseError, match=re.escape("Missing Link in card.")):
        ZillowCardParser(card)


def test_href_is_whitespace_only() -> None:
    """Test when href attribute contains only whitespace."""
    link_html = """
        <a class="property-card-link" data-test="property-card-link" href="   ">
            Property Link
        </a>
    """
    card = create_test_card(link_html)

    # This should raise a ZillowParseError due to missing valid link (whitespace-only href)
    with pytest.raises(ZillowParseError, match=re.escape("Missing Link in card.")):
        ZillowCardParser(card)


def test_multiple_valid_links_takes_first() -> None:
    """Test that when multiple valid links exist, the first one is used."""
    link_html = """
        <a class="property-card-link" data-test="property-card-link" href="/property/first">
            First Link
        </a>
        <a class="property-card-link" data-test="property-card-link" href="/property/second">
            Second Link
        </a>
    """
    card = create_test_card(link_html)
    parser = ZillowCardParser(card)

    assert parser.main_link == "https://www.zillow.com/property/first"


def test_complex_relative_url() -> None:
    """Test with complex relative URL including query parameters."""
    link_html = """
        <a class="property-card-link" data-test="property-card-link" href="/homedetails/123-main-st/456_zpid/?param=value">
            Property Link
        </a>
    """
    card = create_test_card(link_html)
    parser = ZillowCardParser(card)

    assert parser.main_link == "https://www.zillow.com/homedetails/123-main-st/456_zpid/?param=value"


def test_non_string_href_attribute() -> None:
    """Test when href attribute is not a string (edge case)."""
    # Create a card and manually modify the href to be a list (unusual but possible)
    link_html = """
        <a class="property-card-link" data-test="property-card-link" href="/property/123">
            Property Link
        </a>
    """
    card = create_test_card(link_html)

    # Manually modify the href attribute to be non-string
    link_element = card.find("a", class_="property-card-link")
    assert isinstance(link_element, Tag)
    link_element.attrs["href"] = ["not", "a", "string"]  # List instead of string

    # This should raise a ZillowParseError due to invalid href type
    with pytest.raises(ZillowParseError, match=re.escape("Missing Link in card.")):
        ZillowCardParser(card)
