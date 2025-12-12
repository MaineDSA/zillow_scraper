"""Tests for main.py."""

import logging
from collections.abc import Coroutine
from unittest.mock import patch

from _pytest.logging import LogCaptureFixture

from src.config import Config, SubmissionType
from src.main import main


def test_main_with_mocked_configs(caplog: LogCaptureFixture) -> None:
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

    def mock_run_impl(coro: Coroutine) -> None:
        coro.close()  # Close the coroutine to prevent RuntimeWarning

    with patch("src.main.load_configs", return_value=mock_config), patch("src.main.asyncio.run", side_effect=mock_run_impl) as mock_run:
        with caplog.at_level(logging.DEBUG):
            main()

        mock_run.assert_called()
        assert mock_run.call_count == 2
        assert "Processing config: 'config1.env'" in caplog.text
        assert "Completed config: 'config1.env'" in caplog.text
        assert "Processing config: 'config2.env'" in caplog.text
        assert "Completed config: 'config2.env'" in caplog.text
