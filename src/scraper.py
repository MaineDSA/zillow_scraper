"""Zillow scraping and parsing functionality."""

import logging
import re
from dataclasses import dataclass
from random import SystemRandom
from statistics import median
from typing import ClassVar, cast

from bs4 import BeautifulSoup, NavigableString, Tag

from src.constants import ZillowParseError

logger = logging.getLogger(__name__)
cryptogen = SystemRandom()


@dataclass
class PropertyListing:
    """Represents a single property listing."""

    address: str
    price: str
    median_price: str
    link: str


class ZillowCardParser:
    """Handles parsing of individual property cards."""

    # Only compile the patterns that are used multiple times per card
    _PATTERN_NUMERIC = re.compile(r"[^\d,.]")
    _PATTERN_UNIT_COUNT = re.compile(r"(\d+)\s+(?:available\s+)?units?")
    _PATTERN_BED_NUM = re.compile(r"\d+")

    PRICE_CLEANUP_PATTERNS: ClassVar[list[tuple[str, str, re.RegexFlag]]] = [
        (r"\s+\d+\s*bds?(?:\s|$)", "", re.IGNORECASE),
        (r"\+?\s*bd(?:\s|$)", "", re.IGNORECASE),
        (r"\s+", " ", re.NOFLAG),
    ]

    PRICE_REPLACEMENTS: ClassVar[list[str]] = [r"total price", r"studio", r"utilities", r"/mo", r"\+"]

    def _parse_address(self) -> str:
        """Extract address from property card."""
        address_element = self.card.find("address")
        return address_element.get_text(strip=True).replace("|", "") if address_element else ""

    def _parse_main_link(self) -> str:
        """Extract main property link from property card."""
        link_element = self.card.find("a", class_="property-card-link", attrs={"data-test": "property-card-link"})
        if not isinstance(link_element, Tag):
            return ""

        href = cast("str", link_element.get("href", "")).strip()
        return href if href.startswith("http") else f"https://www.zillow.com{href}"

    def _validate_basics(self) -> None:
        """Validate that card has required information."""
        missing = []
        if not self.address.strip():
            missing.append("Address")
        if not self.main_link.strip():
            missing.append("Link")

        if missing:
            error_msg = f"Missing {', '.join(missing)} in card."
            raise ZillowParseError(error_msg)

    def __init__(self, card: Tag) -> None:
        self.card = card
        self.address = self._parse_address()
        self.main_link = self._parse_main_link()
        self._validate_basics()

    def _clean_price_text(self, price_text: str) -> str:
        """Clean and standardize price text."""
        cleaned = price_text

        # Apply regex patterns
        for pattern, replacement, flags in self.PRICE_CLEANUP_PATTERNS:
            cleaned = re.sub(pattern, replacement, cleaned, flags=flags)

        # Apply string replacements
        for replacement in self.PRICE_REPLACEMENTS:
            cleaned = re.sub(replacement, "", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    def _extract_numeric_price(self, price_text: str) -> int | None:
        """Extract numeric value from price text."""
        numeric_only = self._PATTERN_NUMERIC.sub("", price_text).replace(",", "")
        try:
            return int(float(numeric_only))
        except ValueError:
            return None

    def _format_price_range(self, prices: list[str]) -> str | None:
        """Format prices into a range or single price."""
        if not prices:
            return None
        if len(prices) == 1 and self._extract_numeric_price(prices[0]):
            return prices[0]

        price_values: list[tuple[str, int]] = []
        for price in prices:
            value = self._extract_numeric_price(price)
            if value and value > 0:
                price_values.append((price, value))

        if not price_values:
            return None

        price_values.sort(key=lambda x: x[1])
        min_price, max_price = price_values[0][0], price_values[-1][0]

        return min_price if price_values[0][1] == price_values[-1][1] else f"{min_price} - {max_price}"

    def _get_units_count(self) -> int:
        """Extract number of available units."""
        badge_area = self.card.find("div", class_=re.compile(r"StyledPropertyCardBadgeArea"))
        if not badge_area or isinstance(badge_area, NavigableString):
            return 1

        badges = badge_area.find_all("span", class_=re.compile(r"StyledPropertyCardBadge"))
        for badge in badges:
            badge_text = badge.get_text(strip=True).lower()
            unit_match = self._PATTERN_UNIT_COUNT.search(badge_text)
            if unit_match:
                return int(unit_match.group(1))
        return 1

    def _create_specific_link(self, bed_info: str) -> str:
        """Create link with bedroom anchor if applicable."""
        if not bed_info:
            return self.main_link

        bed_info_lower = bed_info.lower()
        if "studio" in bed_info_lower:
            return f"{self.main_link}#bedrooms-0"
        if "bd" in bed_info_lower:
            bed_num = self._PATTERN_BED_NUM.search(bed_info)
            if bed_num:
                return f"{self.main_link}#bedrooms-{bed_num.group()}"

        return self.main_link

    def _get_main_price_listings(self) -> list[PropertyListing]:
        """Extract main price from property card."""
        main_price_element = self.card.find("span", attrs={"data-test": "property-card-price"})
        if not main_price_element:
            return []

        # The price container can contains multiple spans like "Fees may apply".
        # get_text() on the outer span concatenates them without spaces, corrupting
        # the price text (e.g. "$1,608+ 2 bdsFees may apply"). Instead, grab only
        # the first nested span which contains the actual price string.
        inner_span = main_price_element.find("span")
        price_span = inner_span.find("span") if inner_span else None
        raw_text = (price_span or inner_span or main_price_element).get_text(strip=True)

        price_text = self._clean_price_text(raw_text)
        if not price_text:
            return []

        units_count = self._get_units_count()
        address = self.address + (f" ({units_count} units available)" if units_count > 1 else "")

        # Calculate median price (same as regular price for single values)
        numeric_price = self._extract_numeric_price(price_text)
        median_price = str(numeric_price) if numeric_price else price_text

        return [PropertyListing(address, price_text, median_price, self.main_link)]

    def _get_inventory_listings(self) -> list[PropertyListing]:
        """Extract multiple prices from inventory section."""
        inventory_section = self.card.find("div", class_=re.compile(r"property-card-inventory-set"))
        if not inventory_section or isinstance(inventory_section, NavigableString):
            return []

        price_bed_pairs: list[tuple[str, str, str]] = []  # (price, bed_info, link)
        for anchor in inventory_section.find_all("a"):
            box = anchor.find("div", attrs={"data-testid": "PropertyCardInventoryBox"})
            if not box or isinstance(box, NavigableString):
                continue

            spans = box.find_all("span")
            if not spans:
                continue

            price_text = self._clean_price_text(spans[0].get_text(strip=True))
            if not price_text:
                continue

            bed_info = spans[1].get_text(strip=True) if len(spans) > 1 else ""

            href = cast("str", anchor.get("href", "")).strip()
            link = href if href.startswith("http") else f"https://www.zillow.com{href}"

            price_bed_pairs.append((price_text, bed_info, link))

        units_count = self._get_units_count()

        # Handle multiple units with price range
        if units_count > 1 and len(price_bed_pairs) > 1:
            prices = [price for price, _, __ in price_bed_pairs]
            price_range = cast("str", self._format_price_range(prices))

            # Calculate median of the range
            price_values = [self._extract_numeric_price(p) for p in prices]
            price_values = [p for p in price_values if p is not None and p > 0]
            price_values_filtered = [p for p in price_values if p is not None and p > 0]  # mypy being weird
            median_value = str(int(median(price_values_filtered))) if price_values_filtered else price_range

            address = f"{self.address} ({units_count} units available)"
            return [PropertyListing(address, price_range, median_value, self.main_link)]

        # Create individual listings
        listings = []
        for price, bed_info, link in price_bed_pairs:
            address = self.address + (f" ({bed_info})" if bed_info else "")

            # For individual listings, median is same as price
            numeric_price = self._extract_numeric_price(price)
            median_price = str(numeric_price) if numeric_price else price

            listings.append(PropertyListing(address, price, median_price, link))

        return listings

    def parse(self) -> list[PropertyListing]:
        """Parse the card and return all property listings."""
        inventory_listings = self._get_inventory_listings()
        if inventory_listings:
            return inventory_listings

        main_listings = self._get_main_price_listings()
        if not main_listings:
            error_msg = "No valid prices found in card."
            raise ZillowParseError(error_msg)

        return main_listings


class ZillowHomeFinder:
    """Scrape property data from a Zillow soup object."""

    def _parse_soup(self, soup: BeautifulSoup) -> None:
        """Parse all property cards from soup."""
        cards = soup.find_all("article", attrs={"data-test": "property-card"})
        if not cards:
            error_msg = "No property cards found."
            raise ZillowParseError(error_msg)

        logger.debug("Found %d property cards to parse", len(cards))

        for i, card in enumerate(cards):
            try:
                parser = ZillowCardParser(card)
                card_listings = parser.parse()
                logger.debug("Card %d: Found %d entries", i + 1, len(card_listings))
                self.listings.extend(card_listings)
            except ZillowParseError as e:
                logger.error("Skipping card %d due to parse error: %s", i + 1, e)

    def __init__(self, soup: BeautifulSoup) -> None:
        self.listings: list[PropertyListing] = []
        self._parse_soup(soup)

    @property
    def addresses(self) -> list[str]:
        """Get all addresses."""
        return [listing.address for listing in self.listings]

    @property
    def prices(self) -> list[str]:
        """Get all prices."""
        return [listing.price for listing in self.listings]

    @property
    def links(self) -> list[str]:
        """Get all links."""
        return [listing.link for listing in self.listings]
