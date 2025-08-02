import logging
from random import SystemRandom

from patchright.async_api import Error as PlaywrightError
from patchright.async_api import Page

logger = logging.getLogger(__name__)
cryptogen = SystemRandom()


async def scroll_and_load_listings(page: Page, max_entries: int = 100, max_no_change: int = 3, max_scroll_attempts: int = 50) -> None:
    """Scroll through search results to trigger lazy loading."""
    await page.wait_for_selector('[class*="search-page-list-container"]', timeout=10000)

    previous_count = 0
    no_change_iterations = 0

    for iteration in range(max_scroll_attempts):
        current_cards = await page.query_selector_all('article[data-test="property-card"]')
        current_count = len(current_cards)

        msg = f"Iteration {iteration + 1}: Found {current_count} property cards"
        logger.debug(msg)

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
                logger.debug(msg)
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
    logger.debug(msg)

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
