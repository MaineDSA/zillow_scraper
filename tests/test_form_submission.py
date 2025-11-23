from unittest.mock import AsyncMock

import pytest
from patchright.async_api import TimeoutError as PlaywrightTimeoutError

from src.constants import GoogleFormConstants

# Assuming your module is named form_submitter
from src.form_submission import _submit_form


@pytest.fixture
def mock_page() -> AsyncMock:
    """Create a mock Page object with all required methods."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.fill = AsyncMock()
    page.click = AsyncMock()
    page.wait_for_selector = AsyncMock()
    return page


@pytest.fixture
def form_data() -> dict[str, str]:
    """Sample form data for testing."""
    return {
        "url": "https://forms.google.com/test-form",
        "address": "123 Test Street, Test City, TC 12345",
        "price": "$250,000",
        "link": "https://example.com/property",
    }


@pytest.mark.asyncio
async def test_successful_form_submission(mock_page: AsyncMock, form_data: dict[str, str]) -> None:
    """Test successful form submission with all steps completed."""
    # Setup
    mock_page.wait_for_selector.return_value = None  # Success case

    # Execute
    await _submit_form(mock_page, form_data["url"], form_data["address"], form_data["price"], form_data["link"])

    # Verify all steps were called
    mock_page.goto.assert_called_once_with(form_data["url"])
    expected_timeout_call_count = 2
    assert mock_page.wait_for_timeout.call_count == expected_timeout_call_count

    # Verify form fields were filled
    mock_page.fill.assert_any_call(GoogleFormConstants.ADDRESS_INPUT_XPATH, form_data["address"])
    mock_page.fill.assert_any_call(GoogleFormConstants.PRICE_INPUT_XPATH, form_data["price"])
    mock_page.fill.assert_any_call(GoogleFormConstants.LINK_INPUT_XPATH, form_data["link"])

    # Verify form submission
    mock_page.click.assert_called_once_with(GoogleFormConstants.SUBMIT_BUTTON_XPATH)

    # Verify confirmation wait
    mock_page.wait_for_selector.assert_called_once_with('div:has-text("Your response has been recorded")', timeout=5000)


@pytest.mark.asyncio
async def test_form_submission_timeout_error(mock_page: AsyncMock, form_data: dict[str, str]) -> None:
    """Test handling of timeout when waiting for confirmation."""
    # Setup - make wait_for_selector raise TimeoutError
    mock_page.wait_for_selector.side_effect = PlaywrightTimeoutError("Timeout")

    # Execute and verify exception
    with pytest.raises(PlaywrightTimeoutError, match="Form submission confirmation not received"):
        await _submit_form(mock_page, form_data["url"], form_data["address"], form_data["price"], form_data["link"])

    # Verify that all steps before confirmation were still executed
    mock_page.goto.assert_called_once_with(form_data["url"])
    mock_page.fill.assert_any_call(GoogleFormConstants.ADDRESS_INPUT_XPATH, form_data["address"])
    mock_page.fill.assert_any_call(GoogleFormConstants.PRICE_INPUT_XPATH, form_data["price"])
    mock_page.fill.assert_any_call(GoogleFormConstants.LINK_INPUT_XPATH, form_data["link"])
    mock_page.click.assert_called_once_with(GoogleFormConstants.SUBMIT_BUTTON_XPATH)


@pytest.mark.asyncio
async def test_form_submission_with_special_characters(mock_page: AsyncMock) -> None:
    """Test form submission with special characters in inputs."""
    special_data = {
        "url": "https://forms.google.com/test-form?param=value&other=123",
        "address": 'Apartment #5, "The Gardens", Main St. & 2nd Ave.',
        "price": "$1,234,567.89",
        "link": "https://example.com/property?id=123&view=detailed",
    }

    await _submit_form(mock_page, special_data["url"], special_data["address"], special_data["price"], special_data["link"])

    # Verify special characters are handled correctly
    mock_page.goto.assert_called_once_with(special_data["url"])
    mock_page.fill.assert_any_call(GoogleFormConstants.ADDRESS_INPUT_XPATH, special_data["address"])
    mock_page.fill.assert_any_call(GoogleFormConstants.PRICE_INPUT_XPATH, special_data["price"])
    mock_page.fill.assert_any_call(GoogleFormConstants.LINK_INPUT_XPATH, special_data["link"])


@pytest.mark.asyncio
async def test_complete_workflow_simulation() -> None:
    """Simulate a complete workflow with realistic mock behavior."""
    page = AsyncMock()

    # Configure realistic behavior
    page.goto.return_value = None
    page.wait_for_timeout.return_value = None
    page.fill.return_value = None
    page.click.return_value = None
    page.wait_for_selector.return_value = None

    form_data = {
        "url": "https://forms.google.com/real-form",
        "address": "456 Real Street, Real City, RC 67890",
        "price": "$300,000",
        "link": "https://realtor.com/property/123",
    }

    # This should complete without errors
    await _submit_form(page, form_data["url"], form_data["address"], form_data["price"], form_data["link"])

    # Verify all operations were attempted
    assert page.goto.called
    expected_fill_call_count = 3
    assert page.fill.call_count == expected_fill_call_count
    assert page.click.called
    assert page.wait_for_selector.called
    expected_timeout_call_count = 2
    assert page.wait_for_timeout.call_count == expected_timeout_call_count


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("url", "address", "price", "link"),
    [
        ("http://test.com", "123 Main St", "$100,000", "http://link.com"),
        ("https://secure.com", "456 Oak Ave", "$250,000", "https://secure-link.com"),
        ("https://forms.google.com/d/e/test", "789 Pine Rd", "$500,000", "https://example.org"),
    ],
)
async def test_various_input_combinations(url: str, address: str, price: str, link: str) -> None:
    """Test function with various valid input combinations."""
    page = AsyncMock()

    await _submit_form(page, url, address, price, link)

    # Verify inputs were used correctly
    page.goto.assert_called_once_with(url)
    page.fill.assert_any_call(GoogleFormConstants.ADDRESS_INPUT_XPATH, address)
    page.fill.assert_any_call(GoogleFormConstants.PRICE_INPUT_XPATH, price)
    page.fill.assert_any_call(GoogleFormConstants.LINK_INPUT_XPATH, link)
