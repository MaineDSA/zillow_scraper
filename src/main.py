import asyncio
import logging
import re
import time
from random import SystemRandom
from typing import ClassVar

from bs4 import BeautifulSoup, NavigableString, Tag
from patchright.async_api import Page, ViewportSize, async_playwright
from tqdm import tqdm

logger = logging.getLogger(__name__)
cryptogen = SystemRandom()


class ZillowURLs:
    """Constants for Zillow request handling."""

    ZILLOW_URL: ClassVar[str] = "https://www.zillow.com/brunswick-me-04011/rentals/"
    CLONE_URL: ClassVar[str] = "https://appbrewery.github.io/Zillow-Clone/"


class GoogleFormConstants:
    """Constants for Google Form submission."""

    FORM_URL: ClassVar[str] = "https://docs.google.com/forms/d/e/1FAIpQLSfYrPaEL7FXI_wGYiQLUYLuqTijKaE4ZPQTL2LLTGNy6m_cYg/viewform"
    ADDRESS_INPUT_XPATH: ClassVar[str] = 'xpath=//*[@id="mG61Hd"]/div[2]/div/div[2]/div[1]/div/div/div[2]/div/div[1]/div/div[1]/input'
    PRICE_INPUT_XPATH: ClassVar[str] = 'xpath=//*[@id="mG61Hd"]/div[2]/div/div[2]/div[2]/div/div/div[2]/div/div[1]/div/div[1]/input'
    LINK_INPUT_XPATH: ClassVar[str] = 'xpath=//*[@id="mG61Hd"]/div[2]/div/div[2]/div[3]/div/div/div[2]/div/div[1]/div/div[1]/input'
    SUBMIT_BUTTON_XPATH: ClassVar[str] = 'xpath=//*[@id="mG61Hd"]/div[2]/div/div[3]/div/div[1]/div'


class ZillowParseError(Exception):
    """Custom exception for Zillow scraping errors."""


def _parse_address(card: Tag) -> str:
    """Extract address from a property card."""
    address_element = card.find("address")
    if address_element:
        return address_element.get_text(strip=True).replace("|", "")
    return ""


def _parse_main_link(card: Tag) -> str:
    """Extract main property link from a property card."""
    link_element = card.find("a", class_="property-card-link", attrs={"data-test": "property-card-link"})
    if not link_element or isinstance(link_element, NavigableString):
        return ""

    href = link_element.get("href")
    if not isinstance(href, str):
        return ""

    return href if href.startswith("http") else f"https://www.zillow.com{href}"


def _clean_price_text(price_text: str) -> str:
    """Clean and standardize price text."""
    cleaned = re.sub(r"\+?\s*\d+\s*bd?s?", "", price_text, flags=re.IGNORECASE)
    return cleaned.replace("+", "").replace("/mo", "").strip()


def _extract_numeric_price(price_text: str) -> int:
    """Extract numeric value from price text for comparison."""
    # Remove all non-digit characters except commas and periods
    numeric_only = re.sub(r"[^\d,.]", "", price_text)
    # Remove commas
    numeric_only = numeric_only.replace(",", "")
    try:
        return int(float(numeric_only))
    except (ValueError, TypeError):
        return 0


def _format_price_range(prices: list[str]) -> str:
    """Format a list of prices into a range or single price."""
    if not prices:
        return ""

    if len(prices) == 1:
        return prices[0]

    # Extract numeric values for sorting
    price_values = [(price, _extract_numeric_price(price)) for price in prices]
    # Filter out prices that couldn't be parsed
    valid_prices = [(price, value) for price, value in price_values if value > 0]

    if not valid_prices:
        return prices[0]  # Fallback to first price if none could be parsed

    # Sort by numeric value
    valid_prices.sort(key=lambda x: x[1])

    min_price = valid_prices[0][0]
    max_price = valid_prices[-1][0]

    # If min and max are the same, return single price
    if valid_prices[0][1] == valid_prices[-1][1]:
        return min_price

    return f"{min_price} - {max_price}"


def _validate_card_basics(address: str, main_link: str) -> None:
    """Validate that card has required basic information."""
    if not address or not main_link:
        missing = []
        if not address:
            missing.append("Address")
        if not main_link:
            missing.append("Link")
        err = f"Missing {', '.join(missing)} in card."
        raise ZillowParseError(err)


def _extract_available_units_count(card: Tag) -> int:
    """Extract the number of available units from property card badges."""
    badge_area = card.find("div", class_=re.compile(r"StyledPropertyCardBadgeArea"))
    if not badge_area or isinstance(badge_area, NavigableString):
        return 1

    badges = badge_area.find_all("span", class_=re.compile(r"StyledPropertyCardBadge"))
    for badge in badges:
        badge_text = badge.get_text(strip=True).lower()
        # Look for patterns like "2 available units", "3 units available", etc.
        unit_match = re.search(r"(\d+)\s+(?:available\s+)?units?", badge_text)
        if unit_match:
            try:
                return int(unit_match.group(1))
            except ValueError:
                continue

    return 1


def _extract_main_price(card: Tag, address: str, main_link: str) -> list[tuple[str, str, str]]:
    """Extract the main price from the property card."""
    main_price_element = card.find("span", attrs={"data-test": "property-card-price"})
    if not main_price_element:
        return []

    price_text = _clean_price_text(main_price_element.get_text(strip=True))
    if not price_text:
        return []

    # Check if there are multiple available units
    units_count = _extract_available_units_count(card)

    # For main price, we don't create multiple entries for units since there's only one price
    unit_suffix = f" ({units_count} units available)" if units_count > 1 else ""
    final_address = f"{address}{unit_suffix}"

    return [(final_address, price_text, main_link)]


def _create_specific_link(main_link: str, bed_info: str) -> str:
    """Create a specific link with bedroom anchor if bed info is available."""
    if not bed_info or "bd" not in bed_info.lower():
        return main_link

    bed_num = re.search(r"\d+", bed_info)
    if not bed_num:
        return main_link

    return f"{main_link}#bedrooms-{bed_num.group()}"


def _parse_inventory_data(inventory_section: Tag) -> list[tuple[str, str]]:
    """Extract price and bedroom data from inventory section."""
    inventory_prices = inventory_section.find_all("span", class_=re.compile(r"PriceText"))
    inventory_beds = inventory_section.find_all("span", class_=re.compile(r"BedText"))

    results = []
    for i, price_elem in enumerate(inventory_prices):
        price_text = _clean_price_text(price_elem.get_text(strip=True))
        if not price_text:
            continue

        bed_info = ""
        if i < len(inventory_beds):
            bed_info = inventory_beds[i].get_text(strip=True)

        results.append((price_text, bed_info))

    return results


def _create_inventory_entry(address: str, main_link: str, price: str, bed_info: str, units_count: int) -> tuple[str, str, str]:
    """Create a single inventory entry with proper formatting."""
    # Create address with bedroom info
    bed_address = f"{address} ({bed_info})" if bed_info else address

    # Add unit count if multiple units
    if units_count > 1:
        bed_address = f"{bed_address} ({units_count} units available)"

    # Create specific link
    specific_link = _create_specific_link(main_link, bed_info)

    return (bed_address, price, specific_link)


def _extract_inventory_prices(card: Tag, address: str, main_link: str) -> list[tuple[str, str, str]]:
    """Extract multiple prices from the inventory section."""
    inventory_section = card.find("div", class_=re.compile(r"property-card-inventory-set"))
    if not inventory_section or isinstance(inventory_section, NavigableString):
        return []

    # Parse all price/bedroom combinations
    inventory_data = _parse_inventory_data(inventory_section)
    if not inventory_data:
        return []

    # Get unit count
    units_count = _extract_available_units_count(card)

    # If multiple units AND multiple price variations, consolidate into single entry with price range
    if units_count > 1 and len(inventory_data) > 1:
        prices = [price for price, _ in inventory_data]
        price_range = _format_price_range(prices)

        # Create single consolidated address
        final_address = f"{address} ({units_count} units available)"

        return [(final_address, price_range, main_link)]

    # Otherwise, create separate entries for each price/bedroom combination
    results = []
    for price, bed_info in inventory_data:
        entry = _create_inventory_entry(address, main_link, price, bed_info, units_count)
        results.append(entry)

    return results


def _parse_zillow_card(card: Tag) -> list[tuple[str, str, str]]:
    """Parse a single property card and extract all price variations."""
    address = _parse_address(card)
    main_link = _parse_main_link(card)

    _validate_card_basics(address, main_link)

    main_prices = _extract_main_price(card, address, main_link)
    inventory_prices = _extract_inventory_prices(card, address, main_link)

    # Prioritize inventory prices if available, otherwise use main prices
    results = inventory_prices if inventory_prices else main_prices

    if not results:
        msg = "No valid prices found in card."
        raise ZillowParseError(msg)

    return results


async def _submit_form(page: Page, url: str, address: str, price: str, link: str) -> None:
    await page.goto(url)
    await page.wait_for_timeout(cryptogen.randint(1000, 3000))
    await page.fill(GoogleFormConstants.ADDRESS_INPUT_XPATH, address)
    await page.fill(GoogleFormConstants.PRICE_INPUT_XPATH, price)
    await page.fill(GoogleFormConstants.LINK_INPUT_XPATH, link)
    await page.click(GoogleFormConstants.SUBMIT_BUTTON_XPATH)
    await page.wait_for_timeout(cryptogen.randint(1000, 3000))


class ZillowHomeFinder:
    """Scrape property data from a Zillow soup object."""

    def __init__(self, soup: BeautifulSoup) -> None:
        self.addresses: list[str] = []
        self.prices: list[str] = []
        self.links: list[str] = []

        cards = soup.find_all("article", attrs={"data-test": "property-card"})
        if not cards:
            err = "No property cards found."
            raise ZillowParseError(err)

        msg = f"Found {len(cards)} property cards to parse"
        logger.info(msg)

        for i, card in enumerate(cards):
            try:
                card_results = _parse_zillow_card(card)
                msg = f"Card {i + 1}: Found {len(card_results)} entries"
                logger.info(msg)

                for address, price, link in card_results:
                    self.addresses.append(address)
                    self.prices.append(price)
                    self.links.append(link)

            except ZillowParseError as e:
                err = f"Skipping card {i + 1} due to parse error: {e}"
                logger.error(err)

    async def upload_data(self, page: Page, url: str = GoogleFormConstants.FORM_URL) -> None:
        for address, price, link in tqdm(zip(self.addresses, self.prices, self.links, strict=False), total=len(self.prices), unit="entry"):
            await _submit_form(page, url, address, price, link)


async def main(url: str = ZillowURLs.ZILLOW_URL) -> None:
    """Launch browser, scrape Zillow listings, and submit to Google Form."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            viewport=ViewportSize(width=1920, height=1080),
        )
        page = await context.new_page()

        await page.goto(url)
        time.sleep(30)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        home_finder = ZillowHomeFinder(soup)
        await home_finder.upload_data(page)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
