"""
Test cases for Zillow scraper functionality.

These tests validate the parsing logic against real Zillow HTML structure.
"""

# ruff: noqa: PLR2004

from pathlib import Path

import pytest
from bs4 import BeautifulSoup, ResultSet, Tag

from src.scraper import ZillowHomeFinder


@pytest.fixture
def zillow_search_page() -> BeautifulSoup:
    """Load the vendored Zillow search results page."""
    html_path = Path("tests/vendored/zillow-search-boston-20251128-1.html")
    with Path(html_path).open(encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


@pytest.fixture
def property_cards(zillow_search_page: BeautifulSoup) -> ResultSet[Tag]:
    """Extract all property cards from the search page."""
    return zillow_search_page.find_all("article", attrs={"data-test": "property-card"})


class TestZillowHomeFinder:
    """Tests for the main ZillowHomeFinder class."""

    def test_finds_property_listings(self, zillow_search_page: BeautifulSoup) -> None:
        """Check number of property listings found on the page."""
        finder = ZillowHomeFinder(zillow_search_page)
        assert len(finder.listings) == 83

    def test_all_listings_have_required_fields(self, zillow_search_page: BeautifulSoup) -> None:
        """Every listing should have address, price, and link."""
        finder = ZillowHomeFinder(zillow_search_page)
        for listing in finder.listings:
            assert listing.address, "Missing address"
            assert listing.price, "Missing price"
            assert listing.link, "Missing link"

    def test_property_count_matches_visible_cards(self, zillow_search_page: BeautifulSoup, property_cards: ResultSet[Tag]) -> None:
        """Number of listings should match or exceed card count (buildings with multiple listing types)."""
        finder = ZillowHomeFinder(zillow_search_page)
        assert len(finder.listings) >= len(property_cards)

    def test_addresses_property_returns_list(self, zillow_search_page: BeautifulSoup) -> None:
        """Addresses properties should return a list of strings."""
        finder = ZillowHomeFinder(zillow_search_page)
        assert isinstance(finder.addresses, list)
        assert all(isinstance(addr, str) for addr in finder.addresses)

    def test_prices_property_returns_list(self, zillow_search_page: BeautifulSoup) -> None:
        """Prices properties should return a list of strings."""
        finder = ZillowHomeFinder(zillow_search_page)
        assert isinstance(finder.prices, list)
        assert all(isinstance(price, str) for price in finder.prices)

    def test_links_property_returns_list(self, zillow_search_page: BeautifulSoup) -> None:
        """Links properties should return a list of strings."""
        finder = ZillowHomeFinder(zillow_search_page)
        assert isinstance(finder.links, list)
        assert all(isinstance(link, str) for link in finder.links)
