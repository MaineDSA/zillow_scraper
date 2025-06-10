import asyncio
import logging
from random import SystemRandom

import dotenv
from bs4 import BeautifulSoup
from patchright.async_api import ViewportSize, async_playwright

from src.browser_automation import _scroll_and_load_listings
from src.constants import ZillowURLs
from src.scraper import ZillowHomeFinder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
cryptogen = SystemRandom()


async def main() -> None:
    """Launch browser, scrape Zillow listings, and submit to Google Form."""
    dotenv_values = dotenv.dotenv_values(".env")
    url = dotenv_values.get("ZILLOW_URL", ZillowURLs.CLONE_URL)
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
        await _scroll_and_load_listings(page)

        form_url = dotenv_values.get("FORM_URL", None)
        if not form_url:
            err = "Missing URL for Google Form"
            raise ValueError(err)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        await ZillowHomeFinder(soup).upload_data(page, url=form_url)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
