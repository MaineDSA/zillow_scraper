import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from bs4 import BeautifulSoup
from patchright.async_api import ViewportSize, async_playwright

from src.main import ZillowHomeFinder, ZillowURLs, _scroll_and_load_listings


def pytest_runtest_setup(item: pytest_asyncio.plugin.Coroutine) -> None:
    if "requires_browser" in item.keywords and os.getenv("CI"):
        pytest.skip("Browser tests not supported in CI")


@pytest_asyncio.fixture(scope="module")
async def homefinder_clone_live() -> AsyncGenerator[ZillowHomeFinder]:
    """Use Playwright to fetch the Zillow Clone HTML and return a ZillowHomeFinder instance."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            viewport=ViewportSize(width=1920, height=1080),
        )
        page = await context.new_page()
        await page.goto(ZillowURLs.CLONE_URL)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        yield ZillowHomeFinder(soup)

        await browser.close()


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


@pytest_asyncio.fixture(scope="module")
async def homefinder_zillow_local() -> ZillowHomeFinder:
    """Read Zillow HTML from ../zillow.html and return a ZillowHomeFinder instance."""
    html = (Path(__file__).parent / "vendored/zillow-search-04011-20250601.html").read_text()
    soup = BeautifulSoup(html, "html.parser")

    return ZillowHomeFinder(soup)
