"""Browser automation, configuration, and page processing."""

import logging
from random import SystemRandom

from bs4 import BeautifulSoup
from patchright.async_api import Browser, BrowserContext, Page, ViewportSize, async_playwright
from tqdm import tqdm

from src.constants import (
    MAX_SCROLL_DOWN,
    MAX_SCROLL_UP,
    MAX_WAIT_TIME,
    MIN_SCROLL_DOWN,
    MIN_SCROLL_UP,
    MIN_WAIT_TIME,
    PROBABILITY_SCROLL_UP,
    VIEWPORT_HEIGHT,
    VIEWPORT_WIDTH,
)
from src.scraper import PropertyListing, ZillowHomeFinder

logger = logging.getLogger(__name__)
cryptogen = SystemRandom()


async def create_browser_context() -> tuple[Browser, BrowserContext]:
    """Create and configure browser with context."""
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        viewport=ViewportSize(width=VIEWPORT_WIDTH, height=VIEWPORT_HEIGHT),
    )
    return browser, context


# Browser Automation - Scrolling and Navigation


async def get_property_card_count(page: Page) -> int:
    """Get the current count of loaded property cards."""
    cards = await page.query_selector_all('article[data-test="property-card"]')
    return len(cards)


async def is_bottom_element_visible(page: Page) -> bool:
    """Check if the bottom element is visible in the viewport."""
    bottom_element = await page.query_selector("div.search-list-save-search-parent")
    if not bottom_element:
        return False

    return await page.evaluate(
        """
        (element) => {
            const rect = element.getBoundingClientRect();
            return rect.top < window.innerHeight && rect.bottom > 0;
        }
        """,
        bottom_element,
    )


async def scroll_down(page: Page, amount: int) -> None:
    """Scroll down by the specified amount, falling back to window scroll if needed."""
    await page.evaluate(
        f"""
            const searchContainer = document.querySelector('[class*="search-page-list-container"]');
            if (searchContainer) {{
                searchContainer.scrollTop += {amount};
            }} else {{
                window.scrollBy(0, {amount});
            }}
        """
    )


async def perform_human_like_scroll(page: Page) -> None:
    """Perform a human-like scrolling action with random variations."""
    scroll_amount = cryptogen.randint(MIN_SCROLL_DOWN, MAX_SCROLL_DOWN)
    await scroll_down(page, scroll_amount)
    await page.wait_for_timeout(cryptogen.randint(MIN_WAIT_TIME, MAX_WAIT_TIME))

    # Occasionally scroll back up
    if cryptogen.random() < PROBABILITY_SCROLL_UP:
        back_scroll = cryptogen.randint(MIN_SCROLL_UP, MAX_SCROLL_UP)
        await scroll_down(page, -back_scroll)
        await page.wait_for_timeout(cryptogen.randint(MIN_WAIT_TIME, MAX_WAIT_TIME))


async def scroll_to_top(page: Page) -> None:
    """Scroll back to the top of the page."""
    await page.evaluate("""
        const searchContainer = document.querySelector('[class*="search-page-list-container"]');
        if (searchContainer) {
            searchContainer.scrollTop = 0;
        } else {
            window.scrollTo(0, 0);
        }
    """)
    await page.wait_for_timeout(cryptogen.randint(MIN_WAIT_TIME, MAX_WAIT_TIME))


async def scroll_and_load_listings(page: Page, max_entries: int = 100, max_no_change: int = 3, max_scroll_attempts: int = 50) -> None:
    """Scroll through search results to trigger lazy loading."""
    await page.wait_for_selector('[class*="search-page-list-container"]', timeout=10000)

    previous_count = 0
    no_change_iterations = 0

    for iteration in range(max_scroll_attempts):
        current_count = await get_property_card_count(page)
        logger.debug("Iteration %s: Found %s property cards", iteration + 1, current_count)

        # Check stopping conditions
        if current_count >= max_entries:
            logger.info("Reached target of %s entries", max_entries)
            break

        if await is_bottom_element_visible(page):
            logger.debug("Reached bottom of page (search-list-save-search-parent element is visible)")
            break

        # Track stagnation
        if current_count == previous_count:
            no_change_iterations += 1
            if no_change_iterations >= max_no_change:
                logger.warning("No new content loaded after several attempts, stopping")
                break
        else:
            no_change_iterations = 0

        previous_count = current_count

        # Perform scrolling action
        await perform_human_like_scroll(page)

    final_count = await get_property_card_count(page)
    logger.debug("Lazy loading complete. Total property cards loaded: %s", final_count)

    await scroll_to_top(page)


async def check_and_click_next_page(page: Page) -> bool:
    """
    Check if next page button exists and is enabled, then click it.

    Returns True if next page button was clicked, False otherwise.
    """
    try:
        selector = "a[title='Next page']"
        next_button = page.locator(selector).first

        if not next_button:
            logger.warning("No next page button found")
            return False

        # Check if button is enabled (not disabled)
        is_disabled = await next_button.is_disabled()
        is_visible = await next_button.is_visible()

        if is_disabled:
            logger.debug("Next page button found but disabled: %s", selector)
            return False

        if not is_visible:
            logger.debug("Next page button found but not visible: %s", selector)
            return False

        logger.debug("Found enabled next page button with selector: %s", selector)
        await next_button.click()
        await page.wait_for_load_state()
        return True

    except TimeoutError as e:
        logger.warning("Error checking for next page button: %s", e)
        return False


async def sort_by_newest(page: Page) -> None:
    """Sort listings by newest first."""
    sort_button = page.locator("button[id='sort-popover']").first
    if not sort_button:
        logger.error("No sort page button found")
        return

    await sort_button.click()
    await page.wait_for_load_state()

    newest_button = page.get_by_text("Newest")
    if not newest_button:
        logger.error("No sort page by newest button found")
        return

    await newest_button.click()
    await page.wait_for_load_state()


# Page Processing


async def scrape_single_page(page: Page) -> list[PropertyListing]:
    """Scrape listings from a single page."""
    await scroll_and_load_listings(page)

    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")

    finder = ZillowHomeFinder(soup)
    return finder.listings


async def scrape_all_pages(page: Page) -> list[PropertyListing]:
    """Scrape all pages of listings, returning all listings found."""
    all_listings: list[PropertyListing] = []

    page_number = 1
    has_next_page = True
    with tqdm(desc="Scraping pages", unit="page") as pbar:
        while has_next_page:
            logger.debug("Scraping page %s", page_number)

            page_listings = await scrape_single_page(page)
            all_listings.extend(page_listings)
            logger.debug("Found %s listings on page %s", len(page_listings), page_number)

            has_next_page = await check_and_click_next_page(page)
            if not has_next_page:
                logger.debug("No more pages to process or next button is disabled")

            page_number += 1
            pbar.update(1)
            pbar.set_postfix({"listings": len(all_listings)})

    logger.debug("Total listings scraped: %s from %s page(s)", len(all_listings), page_number)
    return all_listings


# Data Processing


def deduplicate_listings(listings: list[PropertyListing]) -> list[PropertyListing]:
    """Deduplicate listings based on unique combination of address, price, and link."""
    seen = set()
    unique_listings = []
    duplicates_removed = 0

    for listing in listings:
        # Create a unique key from the listing
        key = (listing.address, listing.price, listing.link)

        if key not in seen:
            seen.add(key)
            unique_listings.append(listing)
        else:
            duplicates_removed += 1

    if duplicates_removed > 0:
        logger.debug("Removed %s duplicate listings", duplicates_removed)

    logger.debug("Unique listings after deduplication: %s", len(unique_listings))
    return unique_listings
