from pathlib import Path

import pytest
import pytest_asyncio
from bs4 import BeautifulSoup

from src.main import ZillowHomeFinder, ZillowParseError


@pytest_asyncio.fixture(scope="module")
async def homefinder_zillow_local() -> ZillowHomeFinder:
    """Read Zillow HTML from ../zillow.html and return a ZillowHomeFinder instance."""
    html = (Path(__file__).parent / "vendored/zillow-search-04011-20250601.html").read_text()
    soup = BeautifulSoup(html, "html.parser")

    return ZillowHomeFinder(soup)


async def test_homefinder_zillow_local_no_property_cards() -> None:
    """Read Zillow HTML from ../zillow.html and return a ZillowHomeFinder instance."""
    soup = BeautifulSoup("<html></html>", "html.parser")
    with pytest.raises(ZillowParseError, match="No property cards found"):
        ZillowHomeFinder(soup)


async def test_homefinder_local_data_lengths(homefinder_zillow_local: ZillowHomeFinder) -> None:
    address_count = len(homefinder_zillow_local.addresses)
    prices_count = len(homefinder_zillow_local.prices)
    links_count = len(homefinder_zillow_local.links)
    assert address_count == prices_count
    assert prices_count == prices_count
    assert links_count == prices_count


async def test_homefinder_local_sample_addresses(homefinder_zillow_local: ZillowHomeFinder) -> None:
    assert homefinder_zillow_local.addresses[0] == "Atlantic Pointe  10 Townsend Ln, Brunswick, ME (1 bd)"
    assert homefinder_zillow_local.addresses[1] == "Atlantic Pointe  10 Townsend Ln, Brunswick, ME (2 bd)"
    assert homefinder_zillow_local.addresses[2] == "Apartments at Brunswick Landing  5 Captains Way, Brunswick, ME (14 units available)"


async def test_homefinder_local_sample_prices(homefinder_zillow_local: ZillowHomeFinder) -> None:
    assert homefinder_zillow_local.prices[0] == "$2,225"
    assert homefinder_zillow_local.prices[1] == "$2,602"
    assert homefinder_zillow_local.prices[2] == "$1,995 - $2,350"


async def test_homefinder_local_sample_links(homefinder_zillow_local: ZillowHomeFinder) -> None:
    assert homefinder_zillow_local.links[0] == "https://www.zillow.com/b/building/43.90381,-69.918846_ll/#bedrooms-1"
    assert homefinder_zillow_local.links[1] == "https://www.zillow.com/b/building/43.90381,-69.918846_ll/#bedrooms-2"
    assert homefinder_zillow_local.links[2] == "https://www.zillow.com/apartments/brunswick-me/apartments-at-brunswick-landing/CgKVkp/"
