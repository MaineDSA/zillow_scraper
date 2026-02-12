"""Browser automation, configuration, and page processing."""

import logging
import tempfile
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from random import SystemRandom
from typing import Any

from bs4 import BeautifulSoup
from patchright.async_api import BrowserContext, Page, async_playwright
from tqdm import tqdm

from src.constants import (
    MAX_SCROLL_DOWN,
    MAX_SCROLL_UP,
    MAX_WAIT_TIME,
    MIN_SCROLL_DOWN,
    MIN_SCROLL_UP,
    MIN_WAIT_TIME,
    PROBABILITY_SCROLL_UP,
    ZillowParseError,
)
from src.scraper import PropertyListing, ZillowHomeFinder

logger = logging.getLogger(__name__)
cryptogen = SystemRandom()


@asynccontextmanager
async def create_browser_context() -> AsyncGenerator[BrowserContext, Any]:
    """Create and configure browser with Patchright's stealth mode."""
    with tempfile.TemporaryDirectory(prefix="patchright_") as temp_dir:
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=temp_dir,
                channel="chrome",
                headless=False,
                no_viewport=True,
            )

            try:
                yield context
            finally:
                await context.close()


@asynccontextmanager
async def get_browser_page(context: BrowserContext, *, require_new_page: bool = False) -> AsyncGenerator[Page, Any]:
    """Create a browser page ready to use."""
    # Reuse existing page if available, otherwise create new one
    pages = context.pages
    if pages and not require_new_page:
        page = pages[0]
    else:
        page = await context.new_page()

    try:
        yield page
    finally:
        await context.new_page()
        await page.close()


# Browser Automation - Scrolling and Navigation


async def close_modal_if_present(page: Page) -> None:
    """Close modal dialog by clicking button with class containing 'CloseButton', if present."""
    try:
        close_button = page.locator("button[class*='CloseButton']").first
        is_visible = await close_button.is_visible()
        if not is_visible:
            msg = "Popup modal blocked page loading, cannot scrape."
            raise ZillowParseError(msg)
        logger.debug("Popup modal detected, closing it")
        await close_button.click()
    except TimeoutError as e:
        logger.debug("No CloseButton modal found or could not close: %s", e)


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


async def scroll_page(page: Page, amount: int) -> None:
    """Scroll down by the specified amount, falling back to window scroll if needed."""
    result = await page.evaluate(
        f"""
        (() => {{
            const beforeScroll = window.scrollY;
            window.scrollBy(0, {amount});
            const afterScroll = window.scrollY;
            return {{method: 'window', before: beforeScroll, after: afterScroll}};
        }})()
        """
    )
    logger.debug("Scroll result: %s", result)


async def simulate_human_behavior(page: Page) -> None:
    """Simulate human-like mouse movements and pauses."""
    window_dimensions = await page.evaluate("""
        () => ({
            width: window.innerWidth,
            height: window.innerHeight
        })
    """)

    # Move mouse to random positions within the window
    x = cryptogen.randint(100, window_dimensions["width"] - 100)
    y = cryptogen.randint(100, window_dimensions["height"] - 100)
    await page.mouse.move(x, y)

    await page.wait_for_timeout(cryptogen.randint(MIN_WAIT_TIME, MAX_WAIT_TIME))


async def perform_human_like_scroll(page: Page) -> None:
    """Perform a human-like scrolling action with random variations."""
    scroll_amount = cryptogen.randint(MIN_SCROLL_DOWN, MAX_SCROLL_DOWN)
    await scroll_page(page, scroll_amount)
    await simulate_human_behavior(page)

    # Occasionally scroll back up
    if cryptogen.random() < PROBABILITY_SCROLL_UP:
        back_scroll = cryptogen.randint(MIN_SCROLL_UP, MAX_SCROLL_UP)
        await scroll_page(page, -back_scroll)
        await simulate_human_behavior(page)


async def scroll_to_top(page: Page) -> None:
    """Scroll back to the top of the page."""
    await page.evaluate("""
        window.scrollTo(0, 0);
    """)
    await simulate_human_behavior(page)


async def scroll_and_load_listings(page: Page, max_entries: int = 100, max_no_change: int = 3, max_scroll_attempts: int = 50) -> None:
    """Scroll through search results to trigger lazy loading."""
    await page.wait_for_selector('[id="grid-search-results"]', timeout=10000)

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
                logger.warning("No new content loaded after %s attempts, stopping", iteration)
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
    sort_button = page.locator("button[aria-label='Sort Properties']").first

    if not sort_button:
        logger.debug("Sort page styled button not found, looking for popover")
        sort_button = page.locator("button[id='sort-popover']").first

    if not sort_button:
        logger.debug("Sort page popover button not found")
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
    with tqdm(desc="Scraping pages", bar_format="{desc}: page {n} [{elapsed}, {rate_fmt}]{postfix}") as pbar:
        while has_next_page:
            pbar.update(1)
            pbar.set_postfix({"listings": len(all_listings)})

            logger.debug("Scraping page %s", page_number)

            page_listings = await scrape_single_page(page)
            all_listings.extend(page_listings)
            logger.debug("Found %s listings on page %s", len(page_listings), page_number)

            has_next_page = await check_and_click_next_page(page)
            if not has_next_page:
                logger.debug("No more pages to process or next button is disabled")

            page_number += 1

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
