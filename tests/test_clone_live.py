import pytest

from src.main import ZillowHomeFinder


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
