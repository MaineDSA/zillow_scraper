from pathlib import Path

import pytest
from bs4 import BeautifulSoup, ResultSet, Tag


@pytest.fixture
def zillow_search_page_html() -> str:
    """Load the vendored Zillow search results page as html text."""
    html_example_folder = Path("tests/vendored")
    return (html_example_folder / "zillow-search-boston-20251128-1.html").read_text(encoding="utf-8")


@pytest.fixture
def zillow_search_page(zillow_search_page_html: str) -> BeautifulSoup:
    """Create BeautifulSoup object of the vendored Zillow search results page."""
    return BeautifulSoup(zillow_search_page_html, "html.parser")


@pytest.fixture
def property_cards(zillow_search_page: BeautifulSoup) -> ResultSet[Tag]:
    """Extract all property cards from the search page."""
    return zillow_search_page.find_all("article", attrs={"data-test": "property-card"})
