import asyncio
import logging
from random import SystemRandom

from bs4 import BeautifulSoup
from patchright.async_api import ViewportSize, async_playwright

from src.browser_automation import _scroll_and_load_listings
from src.constants import ZillowURLs
from src.scraper import ZillowHomeFinder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
cryptogen = SystemRandom()


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
