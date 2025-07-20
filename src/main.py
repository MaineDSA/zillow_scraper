import asyncio
import logging
from random import SystemRandom

import dotenv
from bs4 import BeautifulSoup
from patchright.async_api import Page, ViewportSize, async_playwright

from src.browser_automation import _scroll_and_load_listings
from src.constants import ZillowURLs
from src.scraper import ZillowHomeFinder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
cryptogen = SystemRandom()


async def check_and_click_next_page(page: Page) -> bool:
    """
    Check if next page button exists and is enabled, then click it.

    Returns True if next page button was clicked, False otherwise.
    """
    try:
        selector = "a[title='Next page']"
        next_button = page.locator(selector).first

        if await next_button.count() > 0:
            # Check if button is enabled (not disabled)
            is_disabled = await next_button.is_disabled()
            is_visible = await next_button.is_visible()

            if not is_disabled and is_visible:
                logger.debug("Found enabled next page button with selector: %s", selector)
                await next_button.click()
                await page.wait_for_load_state()
                return True

            logger.debug("Next page button found but disabled or not visible: %s", selector)
            return False

        logger.warning("No next page button found")
        return False

    except TimeoutError as e:
        logger.warning("Error checking for next page button: %s", e)
        return False


async def main() -> None:
    """Launch browser, scrape Zillow listings, and submit to Google Form."""
    dotenv_values = dotenv.dotenv_values(".env")
    form_url = dotenv_values.get("FORM_URL", None)
    url = dotenv_values.get("SEARCH_URL", ZillowURLs.CLONE_URL)

    if not url:
        err = "Missing URL for scraping"
        raise ValueError(err)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            viewport=ViewportSize(width=1280, height=768),
        )
        page = await context.new_page()

        await page.goto(url)

        page_number = 1

        while True:
            logger.debug("Processing page %s", page_number)

            await _scroll_and_load_listings(page)

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            current_zillow_url = page.url
            await ZillowHomeFinder(soup).upload_data(page, url=form_url)

            await page.goto(current_zillow_url)
            await page.wait_for_load_state()

            if not await check_and_click_next_page(page):
                logger.debug("No more pages to process or next button is disabled")
                break

            page_number += 1
            logger.debug("Moving to page %s", page_number)

        await browser.close()
        logger.debug("Completed processing %s page(s)", page_number)


if __name__ == "__main__":
    asyncio.run(main())
