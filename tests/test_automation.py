"""Tests for automation.py."""

# ruff: noqa: PLR2004

from src.automation import deduplicate_listings
from src.scraper import PropertyListing


def test_deduplicate_no_duplicates() -> None:
    """Test deduplication when all listings are unique."""
    listings = [
        PropertyListing("123 Main St", "$1,000", "https://zillow.com/1"),
        PropertyListing("456 Oak Ave", "$1,200", "https://zillow.com/2"),
        PropertyListing("789 Pine Rd", "$1,500", "https://zillow.com/3"),
    ]

    result = deduplicate_listings(listings)

    assert len(result) == 3
    assert result == listings


def test_deduplicate_exact_duplicates() -> None:
    """Test deduplication when there are exact duplicate listings."""
    listing1 = PropertyListing("123 Main St", "$1,000", "https://zillow.com/1")
    listing2 = PropertyListing("456 Oak Ave", "$1,200", "https://zillow.com/2")
    listing1_dup = PropertyListing("123 Main St", "$1,000", "https://zillow.com/1")

    listings = [listing1, listing2, listing1_dup]

    result = deduplicate_listings(listings)

    assert len(result) == 2
    assert result == [listing1, listing2]


def test_deduplicate_multiple_duplicates() -> None:
    """Test deduplication when there are multiple sets of duplicates."""
    listing1 = PropertyListing("123 Main St", "$1,000", "https://zillow.com/1")
    listing2 = PropertyListing("456 Oak Ave", "$1,200", "https://zillow.com/2")

    listings = [listing1, listing2, listing1, listing2, listing1]

    result = deduplicate_listings(listings)

    assert len(result) == 2
    assert result == [listing1, listing2]


def test_deduplicate_same_address_different_price() -> None:
    """Test that same address with different price is not considered duplicate."""
    listing1 = PropertyListing("123 Main St", "$1,000", "https://zillow.com/1")
    listing2 = PropertyListing("123 Main St", "$1,200", "https://zillow.com/1")

    listings = [listing1, listing2]

    result = deduplicate_listings(listings)

    assert len(result) == 2
    assert result == [listing1, listing2]


def test_deduplicate_same_address_different_link() -> None:
    """Test that same address with different link is not considered duplicate."""
    listing1 = PropertyListing("123 Main St", "$1,000", "https://zillow.com/1")
    listing2 = PropertyListing("123 Main St", "$1,000", "https://zillow.com/2")

    listings = [listing1, listing2]

    result = deduplicate_listings(listings)

    assert len(result) == 2
    assert result == [listing1, listing2]
