from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from bs4 import BeautifulSoup
from patchright.async_api import ViewportSize, async_playwright

from src.browser_automation import scroll_and_load_listings
from src.constants import ZillowURLs
from src.scraper import ZillowHomeFinder


@pytest_asyncio.fixture(scope="module")
async def homefinder_clone_live() -> AsyncGenerator[ZillowHomeFinder]:
    """Fetch the Zillow Clone HTML and return a ZillowHomeFinder instance."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            viewport=ViewportSize(width=1920, height=1080),
        )
        page = await context.new_page()
        await page.goto(ZillowURLs.CLONE_URL)
        await scroll_and_load_listings(page)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        yield ZillowHomeFinder(soup)

        await browser.close()


@pytest.mark.asyncio
async def test_homefinder_clone_data_lengths(homefinder_clone_live: ZillowHomeFinder) -> None:
    address_count = len(homefinder_clone_live.addresses)
    prices_count = len(homefinder_clone_live.prices)
    links_count = len(homefinder_clone_live.links)
    assert address_count == prices_count
    assert prices_count == prices_count
    assert links_count == prices_count


@pytest.mark.asyncio
async def test_homefinder_clone_sample_addresses(homefinder_clone_live: ZillowHomeFinder) -> None:
    assert homefinder_clone_live.addresses[0] == "747 Geary Street, 747 Geary St, Oakland, CA 94609"
    assert homefinder_clone_live.addresses[1] == "Parkmerced  3711 19th Ave, San Francisco, CA"
    assert homefinder_clone_live.addresses[2] == "845 Sutter, 845 Sutter St APT 509, San Francisco, CA"
    assert homefinder_clone_live.addresses[43] == "300 Buchanan, 300 Buchanan St #202, San Francisco, CA 94102"


@pytest.mark.asyncio
async def test_homefinder_clone_sample_prices(homefinder_clone_live: ZillowHomeFinder) -> None:
    assert homefinder_clone_live.prices[0] == "$2,895"
    assert homefinder_clone_live.prices[1] == "$2,810"
    assert homefinder_clone_live.prices[2] == "$2,450"
    assert homefinder_clone_live.prices[43] == "$2,975"


@pytest.mark.asyncio
async def test_homefinder_clone_sample_links_clone(homefinder_clone_live: ZillowHomeFinder) -> None:
    assert homefinder_clone_live.links[0] == "https://www.zillow.com/b/747-geary-street-oakland-ca-CYzGVt/"
    assert homefinder_clone_live.links[1] == "https://www.zillow.com/apartments/san-francisco-ca/parkmerced/5XjKHx/"
    assert homefinder_clone_live.links[42] == "https://www.zillow.com/apartments/san-francisco-ca/1177-market-at-trinity-place/BNjvdD/"
    assert homefinder_clone_live.links[43] == "https://www.zillow.com/apartments/san-francisco-ca/300-buchanan/5XjW2N/"
