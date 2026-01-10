"""Tests for main.py."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

from _pytest.logging import LogCaptureFixture

from src.config import Config, SubmissionType
from src.main import main


async def test_main_with_mocked_configs(caplog: LogCaptureFixture) -> None:
    """Test that main() works with multiple configs."""
    mock_config = [
        Config(
            config_name="config1.env",
            search_url="https://zillow.com",
            submission_type=SubmissionType.FORM,
            form_url="https://form.com",
        ),
        Config(
            config_name="config2.env",
            search_url="https://zillow.com",
            submission_type=SubmissionType.SHEET,
            sheet_url="https://sheets.google.com/spreadsheet",
            sheet_name="Sheet1",
        ),
    ]

    with (
        patch("src.main.load_configs", return_value=mock_config),
        patch("src.main.scrape_and_submit", new_callable=AsyncMock) as mock_scrape_and_submit,
        patch("src.main.create_browser_context") as mock_context,
        caplog.at_level(logging.DEBUG),
    ):
        # Mock the async context manager
        mock_browser_context = MagicMock()
        mock_context.return_value.__aenter__.return_value = mock_browser_context
        mock_context.return_value.__aexit__.return_value = None

        # Run the actual main function
        await main()

        # Verify scrape_and_submit was called twice (once per config)
        assert mock_scrape_and_submit.call_count == 2

        # Verify it was called with the correct configs
        mock_scrape_and_submit.assert_any_call(mock_browser_context, mock_config[0])
        mock_scrape_and_submit.assert_any_call(mock_browser_context, mock_config[1])

        # Verify log messages
        assert "Processing config: 'config1.env'" in caplog.text
        assert "Completed config: 'config1.env'" in caplog.text
        assert "Processing config: 'config2.env'" in caplog.text
        assert "Completed config: 'config2.env'" in caplog.text
