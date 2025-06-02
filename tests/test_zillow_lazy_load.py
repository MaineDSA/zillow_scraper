import os

import pytest

from src.main import ZillowHomeFinder


@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") == "true", reason="Zillow blocks Github Actions.")
async def test_homefinder_zillow_lazy_load(homefinder_zillow_live: ZillowHomeFinder) -> None:
    assert len(homefinder_zillow_live.prices) == 37
