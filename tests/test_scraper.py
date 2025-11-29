"""
Test cases for Zillow scraper functionality.

These tests validate the parsing logic against real Zillow HTML structure.
"""

import logging

# ruff: noqa: PLR2004
from collections.abc import Iterable
from pathlib import Path
from typing import get_args, get_origin

import pytest
from _pytest.logging import LogCaptureFixture
from bs4 import BeautifulSoup, ResultSet, Tag

from src.constants import ZillowParseError
from src.scraper import ZillowCardParser, ZillowHomeFinder


@pytest.fixture
def zillow_search_page() -> BeautifulSoup:
    """Load the vendored Zillow search results page."""
    html_example_folder = Path("tests/vendored")
    html_text = (html_example_folder / "zillow-search-boston-20251128-1.html").read_text(encoding="utf-8")
    return BeautifulSoup(html_text, "html.parser")


@pytest.fixture
def property_cards(zillow_search_page: BeautifulSoup) -> ResultSet[Tag]:
    """Extract all property cards from the search page."""
    return zillow_search_page.find_all("article", attrs={"data-test": "property-card"})


class TestZillowHomeFinder:
    """Tests for the main ZillowHomeFinder class."""

    def test_no_cards_error(self) -> None:
        """Throw parse error when card is skipped."""
        page_html = """
        <!doctype html>
        <html lang="en">
            <head><title>Example Domain</title></head>
            <body><div><p>This domain is for use in documentation examples without needing permission.</div></body>
        </html>
        """
        page = BeautifulSoup(page_html, "html.parser")
        with pytest.raises(ZillowParseError, match="No property cards found"):
            ZillowHomeFinder(page)

    @pytest.mark.parametrize(
        ("card_number", "missing_property"),
        [
            (1, "Address"),
            (2, "Link"),
        ],
        ids=["address", "link"],
    )
    def test_skip_card_parse_errors(self, caplog: LogCaptureFixture, card_number: int, missing_property: str) -> None:
        """Log parse error when card is skipped, but do not raise exception."""
        html_example_folder = Path("tests/vendored")
        html_text = (html_example_folder / "zillow-card-parse-error.html").read_text(encoding="utf-8")
        page = BeautifulSoup(html_text, "html.parser")

        with caplog.at_level(logging.ERROR):
            ZillowHomeFinder(page)
        assert caplog.text.__contains__(f"Skipping card {card_number} due to parse error: Missing {missing_property} in card.")

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
            (
                0,
                [
                    {
                        "address": "95 Saint, 95 Saint Alphonsus St, Roxbury Crossing, MA 02120",
                        "price": "$4,919",
                        "link": "https://www.zillow.com/apartments/boston-ma/95-saint/CkBG9z/",
                    }
                ],
            ),
            (
                1,
                [
                    {
                        "address": "Harper  80 Rugg Rd, Allston, MA (Studio)",
                        "price": "$2,975",
                        "link": "https://www.zillow.com/apartments/allston-ma/harper/Cm4BqX/#bedrooms-0",
                    },
                    {
                        "address": "Harper  80 Rugg Rd, Allston, MA (1bd)",
                        "price": "$3,524",
                        "link": "https://www.zillow.com/apartments/allston-ma/harper/Cm4BqX/#bedrooms-1",
                    },
                    {
                        "address": "Harper  80 Rugg Rd, Allston, MA (2bd)",
                        "price": "$4,333",
                        "link": "https://www.zillow.com/apartments/allston-ma/harper/Cm4BqX/#bedrooms-2",
                    },
                ],
            ),
            (
                3,
                [
                    {
                        "address": "The Longwood  1575 Tremont St, Roxbury Crossing, MA (7 units available)",
                        "price": "$2,850 - $3,761",
                        "link": "https://www.zillow.com/apartments/boston-ma/the-longwood/5XmPS7/",
                    }
                ],
            ),
        ],
        ids=["single_type", "multi_type_prices", "multi_type_price_range"],
    )
    def test_parses_apartments(self, property_cards: ResultSet[Tag], card_number: int, expected_listings: list[dict[str, str]]) -> None:
        """Should parse apartment listings."""
        card = property_cards[card_number]
        parser = ZillowCardParser(card)
        listings = parser.parse()

        assert len(listings) == len(expected_listings)
        for i, listing in enumerate(listings):
            assert expected_listings[i]["address"] == listing.address
            assert expected_listings[i]["price"] == listing.price
            assert expected_listings[i]["link"] == listing.link

    @pytest.mark.parametrize(
        ("input_price", "expected"),
        [
            ("$2,667+ 1 bd", "$2,667"),
            ("$3,000+ 2 bds", "$3,000"),
            ("$2,500+ Studio", "$2,500"),
            ("$2,600+ Total Price", "$2,600"),
        ],
        ids=["bd", "bds", "studio", "total_price"],
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
