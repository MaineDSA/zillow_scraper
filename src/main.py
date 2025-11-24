import asyncio
import logging
import sys
from pathlib import Path
from random import SystemRandom

import dotenv
from bs4 import BeautifulSoup
from patchright.async_api import ViewportSize, async_playwright

from src.browser_automation import check_and_click_next_page, scroll_and_load_listings
from src.constants import ZillowURLs
from src.scraper import ZillowHomeFinder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
cryptogen = SystemRandom()


async def main(form_url: str | None, url: str) -> None:
    """Launch browser, scrape Zillow listings, and submit to Google Form."""
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

        sort_button = page.locator("button[id='sort-popover']").first
        if not sort_button:
            logger.error("No sort page button found")
        else:
            await sort_button.click()
            await page.wait_for_load_state()
            newest_button = page.get_by_text("Newest")
            if not newest_button:
                logger.error("No sort page by newest button found")
            await newest_button.click()
            await page.wait_for_load_state()

        page_number = 1

        while True:
            logger.debug("Processing page %s", page_number)

            await scroll_and_load_listings(page)

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
    for env_file in Path("env/").iterdir():
        dotenv_values = dotenv.dotenv_values(env_file)
        dotenv_form_url = dotenv_values.get("FORM_URL", None)
        dotenv_url = dotenv_values.get("SEARCH_URL", ZillowURLs.CLONE_URL)

        if not dotenv_url:
            logger.error("Missing search url in .env")
            sys.exit()

        msg = f"Processing config: '{env_file}'"
        logger.info(msg)
        asyncio.run(main(dotenv_form_url, dotenv_url))
