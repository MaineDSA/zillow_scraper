"""Tests for form_submission.py."""

import logging
from unittest.mock import AsyncMock, call, patch

import pytest
from _pytest.logging import LogCaptureFixture
from patchright.async_api import TimeoutError as PlaywrightTimeoutError

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


@pytest.fixture
def sample_listings() -> list[PropertyListing]:
    """Create sample listings for testing."""
    return [
        PropertyListing(address="123 Main St", price="$1,500/mo", median_price="1500", link="https://zillow.com/listing/1"),
        PropertyListing(address="456 Oak Ave", price="$2,000/mo", median_price="2000", link="https://zillow.com/listing/2"),
        PropertyListing(address="789 Pine Rd", price="$2,500/mo", median_price="2500", link="https://zillow.com/listing/3"),
    ]


@pytest.mark.asyncio
async def test_submit_listings_partial_failure(caplog: LogCaptureFixture, sample_listings: list[PropertyListing]) -> None:
    """Test that submit_listings continues after individual failures and logs correctly."""
    mock_page = AsyncMock()

    # Make the second submission fail
    call_count = 0

    def wait_for_selector_side_effect(*_, **__) -> AsyncMock:
        nonlocal call_count
        call_count += 1
        if call_count == 2:  # Fail on second call
            msg = "Timeout"
            raise PlaywrightTimeoutError(msg)
        return AsyncMock()

    mock_page.wait_for_selector.side_effect = wait_for_selector_side_effect
    form_url = "https://example.com/form"

    with caplog.at_level("INFO"), patch("src.form_submission.cryptogen.randint", return_value=250):
        await submit_listings(mock_page, form_url, sample_listings)

    assert mock_page.goto.call_count == 3
    assert "2 successful, 1 failed" in caplog.text
    assert "456 Oak Ave" in caplog.text  # Failed listing address should be logged


@pytest.mark.asyncio
async def test_submit_listings_all_succeed(caplog: LogCaptureFixture, sample_listings: list[PropertyListing]) -> None:
    """Test successful submission of all listings."""
    mock_page = AsyncMock()
    form_url = "https://example.com/form"

    with caplog.at_level("INFO"), patch("src.form_submission.cryptogen.randint", return_value=250):
        await submit_listings(mock_page, form_url, sample_listings)

    assert "3 successful, 0 failed" in caplog.text
    assert mock_page.goto.call_count == 3
    assert mock_page.click.call_count == 3


@pytest.mark.asyncio
async def test_submit_listings_all_fail(caplog: LogCaptureFixture, sample_listings: list[PropertyListing]) -> None:
    """Test when all submissions fail."""
    mock_page = AsyncMock()
    mock_page.wait_for_selector.side_effect = PlaywrightTimeoutError("Timeout")
    form_url = "https://example.com/form"

    with caplog.at_level("INFO"), patch("src.form_submission.cryptogen.randint", return_value=250):
        await submit_listings(mock_page, form_url, sample_listings)

    assert "0 successful, 3 failed" in caplog.text
    # All three addresses should appear in error logs
    assert "123 Main St" in caplog.text
    assert "456 Oak Ave" in caplog.text
    assert "789 Pine Rd" in caplog.text


@pytest.mark.asyncio
async def test_submit_single_listing_flow_order() -> None:
    """Test that form submission follows the correct sequence of operations."""
    mock_page = AsyncMock()
    listing = PropertyListing(address="Test Address", price="$1,000", median_price="1000", link="https://test.com")
    form_url = "https://example.com/form"

    # Track call order
    call_order = []
    mock_page.goto.side_effect = lambda _: call_order.append("goto")
    mock_page.fill.side_effect = lambda *_: call_order.append("fill")
    mock_page.click.side_effect = lambda _: call_order.append("click")
    mock_page.wait_for_selector.side_effect = lambda *_, **__: call_order.append("wait_for_selector")
    mock_page.wait_for_timeout.side_effect = lambda _: call_order.append("wait_for_timeout")

    with patch("src.form_submission.cryptogen.randint", return_value=250):
        await _submit_single_listing(mock_page, form_url, listing)

    # Verify the sequence
    assert call_order == [
        "goto",
        "wait_for_timeout",  # After goto
        "fill",  # Address
        "fill",  # Price
        "fill",  # Link
        "click",  # Submit
        "wait_for_selector",  # Confirmation
        "wait_for_timeout",  # Final wait
    ]


@pytest.mark.asyncio
async def test_submit_listings_uses_random_waits() -> None:
    """Test that random wait times are used between submissions."""
    mock_page = AsyncMock()
    listings = [
        PropertyListing("Addr1", "$1000", "1000", "http://link1"),
        PropertyListing("Addr2", "$2000", "2000", "http://link2"),
    ]
    form_url = "https://example.com/form"

    wait_times = []
    mock_page.wait_for_timeout.side_effect = lambda ms: wait_times.append(ms)

    with patch("src.form_submission.cryptogen.randint") as mock_randint:
        # Return different values for each call
        mock_randint.side_effect = [100, 150, 200, 250]
        await submit_listings(mock_page, form_url, listings)

    # Should have wait_for_timeout called multiple times (2 per listing)
    assert len(wait_times) == 4
    # Verify the random values were used
    assert wait_times == [100, 150, 200, 250]


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
    listing = PropertyListing(address="742 Evergreen Terrace", price="$2,500/mo", median_price="2500", link="https://zillow.com/listing/999")
    form_url = "https://example.com/form"

    with patch("src.form_submission.cryptogen.randint", return_value=250):
        await _submit_single_listing(mock_page, form_url, listing)

    fill_calls = mock_page.fill.call_args_list
    assert len(fill_calls) == 3
    assert fill_calls[0] == call(GoogleFormConstants.ADDRESS_INPUT_XPATH, listing.address)
    assert fill_calls[1] == call(GoogleFormConstants.PRICE_INPUT_XPATH, listing.price)
    assert fill_calls[2] == call(GoogleFormConstants.LINK_INPUT_XPATH, listing.link)
