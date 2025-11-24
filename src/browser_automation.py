import logging
from random import SystemRandom

from patchright.async_api import Error as PlaywrightError
from patchright.async_api import Page

logger = logging.getLogger(__name__)
cryptogen = SystemRandom()


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
    try:
        await page.evaluate(f"""
            const searchContainer = document.querySelector('[class*="search-page-list-container"]');
            searchContainer.scrollTop += {amount};
        """)
    except PlaywrightError as e:
        msg = f"Scroll attempt failed: {e}, trying window scroll"
        logger.warning(msg)
        await page.evaluate(f"window.scrollBy(0, {amount})")


async def perform_human_like_scroll(page: Page) -> None:
    """Perform a human-like scrolling action with random variations."""
    scroll_amount = cryptogen.randint(300, 800)
    await scroll_down(page, scroll_amount)
    await page.wait_for_timeout(cryptogen.randint(1000, 4000))

    # Occasionally scroll back up
    scroll_up_chance = 0.15
    if cryptogen.random() < scroll_up_chance:
        back_scroll = cryptogen.randint(100, 300)
        await scroll_down(page, -back_scroll)
        await page.wait_for_timeout(cryptogen.randint(1000, 4000))


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
    await page.wait_for_timeout(cryptogen.randint(1000, 4000))


async def scroll_and_load_listings(page: Page, max_entries: int = 100, max_no_change: int = 3, max_scroll_attempts: int = 50) -> None:
    """Scroll through search results to trigger lazy loading."""
    await page.wait_for_selector('[class*="search-page-list-container"]', timeout=10000)

    previous_count = 0
    no_change_iterations = 0

    for iteration in range(max_scroll_attempts):
        current_count = await get_property_card_count(page)
        msg = f"Iteration {iteration + 1}: Found {current_count} property cardsIteration {iteration + 1}: Found {current_count} property cards"
        logger.debug(msg)

        # Check stopping conditions
        if current_count >= max_entries:
            msg = f"Reached target of {max_entries} entries"
            logger.info(msg)
            break

        if await is_bottom_element_visible(page):
            msg = "Reached bottom of page (search-list-save-search-parent element is visible)"
            logger.debug(msg)
            break

        # Track stagnation
        if current_count == previous_count:
            no_change_iterations += 1
            if no_change_iterations >= max_no_change:
                logger.info("No new content loaded after several attempts, stopping")
                break
        else:
            no_change_iterations = 0

        previous_count = current_count

        # Perform scrolling action
        await perform_human_like_scroll(page)

    final_count = await get_property_card_count(page)
    msg = f"Lazy loading complete. Total property cards loaded: {final_count}"
    logger.debug(msg)

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
