from unittest.mock import AsyncMock, MagicMock

import pytest

from src.main import _scroll_and_load_listings


@pytest.mark.asyncio
async def test_scroll_stops_at_bottom_element() -> None:
    """Test that scroll function stops when it finds the bottom element."""
    mock_page = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()

    # Mock property cards (simulate finding some cards)
    mock_page.query_selector_all.return_value = [MagicMock() for _ in range(10)]

    # Mock bottom element found on second iteration
    mock_page.query_selector.side_effect = [
        None,  # First iteration - no bottom element
        MagicMock(),  # Second iteration - bottom element found
    ]

    mock_page.evaluate = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()

    await _scroll_and_load_listings(mock_page, max_entries=100, max_scroll_attempts=10)

    # Should have called query_selector twice (once per iteration before stopping)
    assert mock_page.query_selector.call_count == 2
    # Should have called query_selector with the correct CSS selector
    mock_page.query_selector.assert_called_with("div.search-list-save-search-parent")


@pytest.mark.asyncio
async def test_scroll_continues_when_no_bottom_element() -> None:
    """Test that scroll function continues when bottom element is not found."""
    mock_page = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()

    # Mock property cards that don't change (to trigger no_change_iterations)
    mock_page.query_selector_all.return_value = [MagicMock() for _ in range(5)]

    # Mock bottom element never found
    mock_page.query_selector.return_value = None

    mock_page.evaluate = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()

    await _scroll_and_load_listings(mock_page, max_entries=100, max_no_change=3, max_scroll_attempts=10)

    # Should have called query_selector multiple times before stopping due to no_change_iterations
    assert mock_page.query_selector.call_count >= 3
    """Test handling when initial selector times out."""
    mock_page = AsyncMock()
    mock_page.wait_for_selector.side_effect = Exception("Timeout waiting for selector")

    # Should raise the timeout exception
    with pytest.raises(Exception, match="Timeout waiting for selector"):
        await _scroll_and_load_listings(mock_page)
