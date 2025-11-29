"""
Test cases for Zillow scraper functionality.

These tests validate the parsing logic against real Zillow HTML structure.
"""

# ruff: noqa: PLR2004

from collections.abc import Iterable
from pathlib import Path
from typing import get_args, get_origin

import pytest
from bs4 import BeautifulSoup, ResultSet, Tag

from src.scraper import ZillowCardParser, ZillowHomeFinder


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

    @pytest.mark.parametrize(
        ("property_name", "property_type_full"),
        [
            ("addresses", list[str]),
            ("prices", list[str]),
            ("links", list[str]),
        ],
        ids=["addresses", "prices", "links"],
    )
    def test_listing_property_returns_type(self, zillow_search_page: BeautifulSoup, property_name: str, property_type_full: type) -> None:
        """Properties should return a list of strings."""
        finder = ZillowHomeFinder(zillow_search_page)
        listing_property = getattr(finder, property_name)

        property_type_origin = get_origin(property_type_full)
        assert isinstance(property_type_origin, type)
        property_type_arg = get_args(property_type_full)[0]
        assert isinstance(property_type_arg, type)

        assert isinstance(listing_property, property_type_origin)
        assert isinstance(listing_property, Iterable)  # needed for typechecker
        assert all(isinstance(listing_property_item, property_type_arg) for listing_property_item in listing_property)


class TestZillowCardParser:
    """Tests for individual property card parsing."""

    @pytest.mark.parametrize(
        ("card_number", "expected_listings"),
        [
            (0, [{"address": "95 Saint Alphonsus St, Roxbury Crossing, MA", "price": "$4,919", "link": "zillow.com/apartments/boston-ma/95-saint/CkBG9z"}]),
            (
                1,
                [
                    {"address": "80 Rugg Rd, Allston, MA", "price": "$2,975", "link": "zillow.com/apartments/allston-ma/harper/Cm4BqX"},
                    {"address": "80 Rugg Rd, Allston, MA", "price": "$3,524", "link": "zillow.com/apartments/allston-ma/harper/Cm4BqX"},
                    {"address": "80 Rugg Rd, Allston, MA", "price": "$4,333", "link": "zillow.com/apartments/allston-ma/harper/Cm4BqX"},
                ],
            ),
            (
                3,
                [
                    {
                        "address": "1575 Tremont St, Roxbury Crossing, MA",
                        "price": "$2,850 - $3,761",
                        "link": "zillow.com/apartments/boston-ma/the-longwood/5XmPS7",
                    }
                ],
            ),
        ],
        ids=["Single Listing Type", "Multiple Listing Types", "Price Range"],
    )
    def test_parses_apartments(self, property_cards: ResultSet[Tag], card_number: int, expected_listings: list[dict[str, str]]) -> None:
        """Should parse apartment listings."""
        card = property_cards[card_number]
        parser = ZillowCardParser(card)
        listings = parser.parse()

        assert len(listings) == len(expected_listings)
        for i, listing in enumerate(listings):
            assert expected_listings[i]["address"] in listing.address
            assert expected_listings[i]["price"] in listing.price
            assert expected_listings[i]["link"] in listing.link

    @pytest.mark.parametrize(
        ("input_price", "expected"),
        [
            ("$2,667+ 1 bd", "$2,667"),
            ("$3,000+ 2 bds", "$3,000"),
            ("$2,500+ Studio", "$2,500"),
            ("$2,600+ Total Price", "$2,600"),
        ],
        ids=["bd", "bds", "studio", "total price"],
    )
    def test_price_cleaning_removes_extra_text(self, property_cards: ResultSet[Tag], input_price: str, expected: str) -> None:
        """Price cleaning should remove unwanted text."""
        card = property_cards[0]
        parser = ZillowCardParser(card)
        cleaned = parser._clean_price_text(input_price)
        assert cleaned == expected

    def test_bedroom_specific_links(self, property_cards: ResultSet[Tag]) -> None:
        """Should create bedroom-specific anchor links when applicable."""
        card = property_cards[1]  # Multi-unit, multi-type building
        parser = ZillowCardParser(card)
        listings = parser.parse()

        # Check if listing has bedroom anchors
        assert any("#bedrooms-" in listing.link for listing in listings)

    def test_units_count_extraction(self, property_cards: ResultSet[Tag]) -> None:
        """Should extract units available count for listing with 'available units'."""
        card = property_cards[21]  # Multi-unit with 'available units' shown
        parser = ZillowCardParser(card)
        units = parser._get_units_count()
        assert units > 1
        listings = parser.parse()
        assert all("10 units available" in listing.address for listing in listings)

    def test_units_price_range_extraction(self, property_cards: ResultSet[Tag]) -> None:
        """Should extract price range for listing with 'available units'."""
        card = property_cards[21]  # Multi-unit with 'available units' shown
        parser = ZillowCardParser(card)
        units = parser._get_units_count()
        assert units > 1
        listings = parser.parse()
        assert all(" - " in listing.price for listing in listings)
