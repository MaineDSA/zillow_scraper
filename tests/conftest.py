import os

import pytest
import pytest_asyncio


def pytest_runtest_setup(item: pytest_asyncio.plugin.Coroutine) -> None:
    if "requires_browser" in item.keywords and os.getenv("CI"):
        pytest.skip("Browser tests not supported in CI")
