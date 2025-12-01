"""Tests for form_submission.py."""

# ruff: noqa: PLR2004

import logging
from unittest.mock import AsyncMock, call, patch

import pytest
from _pytest.logging import LogCaptureFixture

from src.constants import GoogleFormConstants
from src.form_submission import _submit_single_listing, submit_listings
from src.scraper import PropertyListing


@pytest.fixture
def mock_page() -> AsyncMock:
    """Create a mock page object."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.fill = AsyncMock()
    page.click = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    return page


@pytest.mark.parametrize(
    "empty_list_arg",
    [
        [],
        None,
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


@pytest.mark.asyncio
async def test_submit_single_listing_field_mapping(mock_page: AsyncMock) -> None:
    """Test that form fields are filled in the correct order with correct selectors."""
    listing = PropertyListing(address="742 Evergreen Terrace", price="$2,500/mo", link="https://zillow.com/listing/999")
    form_url = "https://example.com/form"

    with patch("src.form_submission.cryptogen.randint", return_value=250):
        await _submit_single_listing(mock_page, form_url, listing)

    fill_calls = mock_page.fill.call_args_list
    assert len(fill_calls) == 3
    assert fill_calls[0] == call(GoogleFormConstants.ADDRESS_INPUT_XPATH, listing.address)
    assert fill_calls[1] == call(GoogleFormConstants.PRICE_INPUT_XPATH, listing.price)
    assert fill_calls[2] == call(GoogleFormConstants.LINK_INPUT_XPATH, listing.link)
