import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from bs4 import BeautifulSoup
from patchright.async_api import ViewportSize, async_playwright

from src.browser_automation import _scroll_and_load_listings
from src.constants import ZillowURLs
from src.scraper import ZillowHomeFinder


@pytest_asyncio.fixture(scope="module")
async def homefinder_zillow_live() -> AsyncGenerator[ZillowHomeFinder]:
    """Use Playwright to fetch live Zillow HTML and return a ZillowHomeFinder instance."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            viewport=ViewportSize(width=1920, height=1080),
        )
        page = await context.new_page()
        await page.goto(ZillowURLs.ZILLOW_URL)
        await _scroll_and_load_listings(page)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        yield ZillowHomeFinder(soup)

        await browser.close()


@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") == "true", reason="Zillow blocks Github Actions.")
async def test_homefinder_zillow_lazy_load(homefinder_zillow_live: ZillowHomeFinder) -> None:
    assert len(homefinder_zillow_live.prices) > 30
