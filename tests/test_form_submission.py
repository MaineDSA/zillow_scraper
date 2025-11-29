"""Test for empty listings in submit_listings function."""

import logging
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from _pytest.logging import LogCaptureFixture

from src.form_submission import submit_listings

if TYPE_CHECKING:
    from src.scraper import PropertyListing


@pytest.mark.parametrize(
    ("empty_list_arg"),
    [
        ([]),
        (None),
    ],
    ids=["empty_list", "none"],
)
@pytest.mark.asyncio
async def test_submit_listings_with_empty_list(caplog: LogCaptureFixture, empty_list_arg: list | None) -> None:
    """Test that submit_listings handles empty list gracefully."""
    mock_page = AsyncMock()
    form_url = "https://example.com/form"
    empty_listings: list[PropertyListing] = empty_list_arg  # type: ignore[assignment]

    with caplog.at_level(logging.WARNING):
        await submit_listings(mock_page, form_url, empty_listings)

        assert "No listings to submit" in caplog.text
        mock_page.goto.assert_not_called()
        mock_page.fill.assert_not_called()
        mock_page.click.assert_not_called()
