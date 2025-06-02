import asyncio
import logging
import re
from random import SystemRandom
from typing import ClassVar

from bs4 import BeautifulSoup, NavigableString, Tag
from patchright.async_api import Error as PlaywrightError
from patchright.async_api import Page, ViewportSize, async_playwright
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
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


async def _scroll_and_load_listings(page: Page, max_entries: int = 100, max_no_change: int = 3, max_scroll_attempts: int = 50) -> None:
    """Scroll through search results to trigger lazy loading."""
    await page.wait_for_selector('[class*="search-page-list-container"]', timeout=10000)

    previous_count = 0
    no_change_iterations = 0

    for iteration in range(max_scroll_attempts):
        current_cards = await page.query_selector_all('article[data-test="property-card"]')
        current_count = len(current_cards)

        msg = f"Iteration {iteration + 1}: Found {current_count} property cards"
        logger.info(msg)

        if current_count >= max_entries:
            msg = f"Reached target of {max_entries} entries"
            logger.info(msg)
            break

        # Check if we've reached the bottom of the page (element is visible on screen)
        bottom_element = await page.query_selector("div.search-list-save-search-parent")
        if bottom_element:
            # Check if the element is actually visible in the viewport
            is_visible = await page.evaluate(
                """
                (element) => {
                    const rect = element.getBoundingClientRect();
                    return rect.top < window.innerHeight && rect.bottom > 0;
                }
            """,
                bottom_element,
            )

            if is_visible:
                msg = "Reached bottom of page (search-list-save-search-parent element is visible)"
                logger.info(msg)
                break

        if current_count == previous_count:
            no_change_iterations += 1
            if no_change_iterations >= max_no_change:
                logger.info("No new content loaded after several attempts, stopping")
                break
        else:
            no_change_iterations = 0

        previous_count = current_count

        # Scroll down by a random amount (simulate human-like scrolling)
        scroll_amount = cryptogen.randint(300, 800)

        try:
            await page.evaluate(f"""
                const searchContainer = document.querySelector('[class*="search-page-list-container"]');
                searchContainer.scrollTop += {scroll_amount};
            """)
        except PlaywrightError as e:
            wrn = f"Scroll attempt failed: {e}, trying window scroll"
            logger.warning(wrn)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")

        # Random wait time between scrolls (1-4 seconds)
        wait_time = cryptogen.randint(1000, 4000)
        await page.wait_for_timeout(wait_time)

        # Occasionally scroll back up a bit to simulate more natural browsing
        scroll_up_chance: float = 0.15
        if iteration > 0 and cryptogen.random() < scroll_up_chance:
            back_scroll = cryptogen.randint(100, 300)
            try:
                await page.evaluate(f"""
                    const searchContainer = document.querySelector('[class*="search-page-list-container"]');
                    searchContainer.scrollTop += {back_scroll};
                """)
            except PlaywrightError as e:
                wrn = f"Scroll attempt failed: {e}, trying window scroll"
                logger.warning(wrn)
                await page.evaluate(f"window.scrollBy(0, -{back_scroll})")

            await page.wait_for_timeout(cryptogen.randint(500, 1500))

    final_cards = await page.query_selector_all('article[data-test="property-card"]')
    final_count = len(final_cards)
    msg = f"Lazy loading complete. Total property cards loaded: {final_count}"
    logger.info(msg)

    # Scroll back to top to ensure all content is properly rendered
    await page.evaluate("""
        const searchContainer = document.querySelector('[class*="search-page-list-container"]');
        if (searchContainer) {
            searchContainer.scrollTop = 0;
        } else {
            window.scrollTo(0, 0);
        }
    """)
    await page.wait_for_timeout(1500)


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
    cleaned = re.sub(r"\+?\s*\d+\s*bds?(?:\s|$)", "", price_text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\+?\s*bd(?:\s|$)", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("utilities", "")
    cleaned = cleaned.replace("/mo", "")
    cleaned = cleaned.replace("+", "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _extract_numeric_price(price_text: str) -> int:
    """Extract numeric value from price text for comparison."""
    numeric_only = re.sub(r"[^\d,.]", "", price_text).replace(",", "")
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

    price_values = [(price, _extract_numeric_price(price)) for price in prices]
    valid_prices = [(price, value) for price, value in price_values if value > 0]
    if not valid_prices:
        return prices[0]
    valid_prices.sort(key=lambda x: x[1])

    min_price = valid_prices[0][0]
    max_price = valid_prices[-1][0]
    if valid_prices[0][1] == valid_prices[-1][1]:
        return min_price

    return f"{min_price} - {max_price}"


def _validate_card_basics(address: str, main_link: str) -> None:
    """Validate that card has required basic information."""
    if not address or not address.strip() or not main_link or not main_link.strip():
        missing = []
        if not address or not address.strip():
            missing.append("Address")
        if not main_link or not main_link.strip():
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

    units_count = _extract_available_units_count(card)

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
    bed_address = f"{address} ({bed_info})" if bed_info else address

    if units_count > 1:
        bed_address = f"{bed_address} ({units_count} units available)"

    specific_link = _create_specific_link(main_link, bed_info)

    return bed_address, price, specific_link


def _extract_inventory_prices(card: Tag, address: str, main_link: str) -> list[tuple[str, str, str]]:
    """Extract multiple prices from the inventory section."""
    inventory_section = card.find("div", class_=re.compile(r"property-card-inventory-set"))
    if not inventory_section or isinstance(inventory_section, NavigableString):
        return []

    # Parse all price/bedroom combinations
    inventory_data = _parse_inventory_data(inventory_section)
    if not inventory_data:
        return []

    units_count = _extract_available_units_count(card)

    if units_count > 1 and len(inventory_data) > 1:
        prices = [price for price, _ in inventory_data]
        price_range = _format_price_range(prices)
        final_address = f"{address} ({units_count} units available)"

        return [(final_address, price_range, main_link)]

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
        self.cards: list[Tag] = []
        self.addresses: list[str] = []
        self.prices: list[str] = []
        self.links: list[str] = []

        self.cards = soup.find_all("article", attrs={"data-test": "property-card"})
        if not self.cards:
            err = "No property cards found."
            raise ZillowParseError(err)

        msg = f"Found {len(self.cards)} property cards to parse"
        logger.info(msg)

        for i, card in enumerate(self.cards):
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
            viewport=ViewportSize(width=1280, height=768),
        )
        page = await context.new_page()

        await page.goto(url)

        await _scroll_and_load_listings(page)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        home_finder = ZillowHomeFinder(soup)
        await home_finder.upload_data(page)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
