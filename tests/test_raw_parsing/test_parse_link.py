from unittest.mock import Mock

from bs4 import BeautifulSoup, NavigableString, Tag

from src.parsers import _parse_main_link


def test_valid_absolute_url() -> None:
    """Test with valid absolute URL."""
    html = """
        <div>
            <a class="property-card-link" data-test="property-card-link" href="https://www.zillow.com/property/123">
                Property Link
            </a>
        </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div")
    assert isinstance(card, Tag)

    result = _parse_main_link(card)
    assert result == "https://www.zillow.com/property/123"


def test_valid_relative_url() -> None:
    """Test with valid relative URL."""
    html = """
        <div>
            <a class="property-card-link" data-test="property-card-link" href="/property/456">
                Property Link
            </a>
        </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div")
    assert isinstance(card, Tag)

    result = _parse_main_link(card)
    assert result == "https://www.zillow.com/property/456"


def test_no_link_element_found() -> None:
    """Test when no matching link element is found."""
    html = """
        <div>
            <a class="different-class" href="/property/123">
                Not the right link
            </a>
            <span>Some other content</span>
        </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div")
    assert isinstance(card, Tag)

    result = _parse_main_link(card)
    assert result == ""


def test_link_element_is_none() -> None:
    """Test when find() returns None."""
    html = "<div></div>"
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div")
    assert isinstance(card, Tag)

    result = _parse_main_link(card)
    assert result == ""


def test_link_element_is_navigable_string() -> None:
    """Test when find() returns a NavigableString instead of Tag."""
    # This is a tricky case to create naturally, so we'll mock it
    card = Mock()
    navigable_string = NavigableString("some text")
    card.find.return_value = navigable_string

    result = _parse_main_link(card)
    assert result == ""


def test_wrong_class_name() -> None:
    """Test with link that has wrong class name."""
    html = """
        <div>
            <a class="wrong-class" data-test="property-card-link" href="/property/123">
                Property Link
            </a>
        </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div")
    assert isinstance(card, Tag)

    result = _parse_main_link(card)
    assert result == ""


def test_wrong_data_test_attribute() -> None:
    """Test with link that has wrong data-test attribute."""
    html = """
        <div>
            <a class="property-card-link" data-test="wrong-test" href="/property/123">
                Property Link
            </a>
        </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div")
    assert isinstance(card, Tag)

    result = _parse_main_link(card)
    assert result == ""


def test_missing_data_test_attribute() -> None:
    """Test with link that's missing data-test attribute."""
    html = """
        <div>
            <a class="property-card-link" href="/property/123">
                Property Link
            </a>
        </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div")
    assert isinstance(card, Tag)

    result = _parse_main_link(card)
    assert result == ""


def test_href_is_none() -> None:
    """Test when href attribute is None."""
    html = """
        <div>
            <a class="property-card-link" data-test="property-card-link">
                Property Link (no href)
            </a>
        </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div")
    assert isinstance(card, Tag)

    result = _parse_main_link(card)
    assert result == ""


def test_href_is_empty_string() -> None:
    """Test when href attribute is empty string."""
    html = """
        <div>
            <a class="property-card-link" data-test="property-card-link" href="">
                Property Link
            </a>
        </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div")
    assert isinstance(card, Tag)

    result = _parse_main_link(card)
    assert result == "https://www.zillow.com"
