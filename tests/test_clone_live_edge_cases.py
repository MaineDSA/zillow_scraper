
import pytest
from patchright.async_api import ViewportSize, async_playwright

from src.main import ZillowURLs, _scroll_and_load_listings


@pytest.mark.asyncio
async def test_homefinder_clone_max_scrolls() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            viewport=ViewportSize(width=1920, height=1080),
        )
        page = await context.new_page()
        await page.goto(ZillowURLs.CLONE_URL)
        await _scroll_and_load_listings(page, max_scroll_attempts=3)
        await browser.close()


@pytest.mark.asyncio
async def test_homefinder_clone_max_entries() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            viewport=ViewportSize(width=1920, height=1080),
        )
        page = await context.new_page()
        await page.goto(ZillowURLs.CLONE_URL)
        await _scroll_and_load_listings(page, max_entries=11)
        await browser.close()
