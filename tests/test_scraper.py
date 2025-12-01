"""
Test cases for Zillow scraper functionality.

These tests validate the parsing logic against real Zillow HTML structure.
"""

# ruff: noqa: PLR2004

import logging
from collections.abc import Iterable
from pathlib import Path
from typing import get_args, get_origin

import pytest
from _pytest.logging import LogCaptureFixture
from bs4 import BeautifulSoup, ResultSet, Tag

from src.constants import ZillowParseError
from src.scraper import ZillowCardParser, ZillowHomeFinder


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
            (3, "Address, Link"),
        ],
        ids=["address", "link", "address_and_link"],
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

    def test_numeric_price_extraction_exception_handling(self, property_cards: ResultSet[Tag]) -> None:
        """Invalid strings shouldn't raise ValueError."""
        card = property_cards[0]
        parser = ZillowCardParser(card)
        assert not parser._extract_numeric_price("1.500.00")

    @pytest.mark.parametrize(
        ("input_prices", "expected"),
        [
            ([], None),
            (["Wouldn't you like to know", "Call for price"], None),
            (["$1,000"], "$1,000"),
            (["$1,000", "Call for price"], "$1,000"),
        ],
        ids=["empty_list", "no_usable_prices", "one_price", "usable_and_unusable_prices"],
    )
    def test_format_price_range_guard_clauses(self, property_cards: ResultSet[Tag], input_prices: list[str], expected: str | None) -> None:
        """Invalid strings shouldn't raise ValueError."""
        card = property_cards[0]
        parser = ZillowCardParser(card)
        assert parser._format_price_range(input_prices) == expected

    def test_no_badge_area_returns_1(self) -> None:
        """Test when badge area is not found (badge_area is None)."""
        html = """
        <article data-test="property-card">
            <address>123 Main St</address>
            <a class="property-card-link" data-test="property-card-link" href="/homedetails/123">Link</a>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        card = soup.find("article")
        assert isinstance(card, Tag)
        parser = ZillowCardParser(card)
        units_count = parser._get_units_count()
        assert units_count == 1

    @pytest.mark.parametrize(
        "bed_info",
        [
            "",
            "bd",
            "4 beds",
            "bedrooms",
            "3 bedrooms",
        ],
        ids=["bd_empty_string", "bd_no_number", "beds_with_number", "bedrooms_no_number", "bedrooms_with_number"],
    )
    def test_create_specific_link_improper_bed_info(self, property_cards: ResultSet[Tag], bed_info: str) -> None:
        """Test behavior of _create_specific_link when number of beds is not present in expected format."""
        card = property_cards[0]
        parser = ZillowCardParser(card)
        result = parser._create_specific_link(bed_info)
        assert "#bedrooms" not in result

    @pytest.mark.parametrize(
        "price_text",
        [
            "",
            "   Total Price     ",
        ],
        ids=["price_empty_string", "price_empty_after_cleaning"],
    )
    def test_returns_empty_when_price_element_exists_but_empty(self, price_text: str) -> None:
        """Test that empty list is returned when price element exists but has no text."""
        html = f"""
        <article data-test="property-card">
            <address>123 Main St</address>
            <a class="property-card-link" data-test="property-card-link" href="/property/123">Link</a>
            <span data-test="property-card-price">{price_text}</span>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        card = soup.find("article")
        assert isinstance(card, Tag)
        parser = ZillowCardParser(card)
        result = parser._get_main_price_listings()
        assert result == []

    @pytest.mark.parametrize(
        "price_element",
        [
            "",
            '<span data-test="property-card-price">     </span>',
            '<span data-test="property-card-price">  Total Price   </span>',
        ],
        ids=["price_missing", "price_empty", "price_cleaned"],
    )
    def test_parse_raises_error_when_price_invalid_or_missing(self, price_element: str) -> None:
        """Test error raised when card has no inventory and price is only whitespace."""
        html = f"""
        <article data-test="property-card">
            <address>456 Oak Ave</address>
            <a class="property-card-link" data-test="property-card-link" href="/property/456">Link</a>
            {price_element}
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        card = soup.find("article")
        assert isinstance(card, Tag)
        parser = ZillowCardParser(card)

        with pytest.raises(ZillowParseError, match="No valid prices found in card"):
            parser.parse()

    @pytest.mark.parametrize(
        ("price_text", "bed_text"),
        [
            ("", "2 bd"),
            ("bd", "Studio"),
        ],
        ids=["price_text_empty", "price_text_cleaned"],
    )
    def test_get_inventory_listings_with_empty_prices(self, price_text: str, bed_text: str) -> None:
        """Test that _get_inventory_listings returns an empty list when inventory set price text is empty."""
        html = f"""
        <article data-test="property-card">
            <address>123 Test St</address>
            <a class="property-card-link" data-test="property-card-link" href="/test">Link</a>
            <div class="property-card-inventory-set-random123">
                <span class="PriceText-random123">{price_text}</span>
                <span class="BedText-random123">{bed_text}</span>
            </div>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        card = soup.find("article")
        assert isinstance(card, Tag)
        parser = ZillowCardParser(card)

        listings = parser._get_inventory_listings()
        assert listings == []
