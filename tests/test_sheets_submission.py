import logging
from unittest.mock import MagicMock, patch

import pytest
from _pytest.logging import LogCaptureFixture

from src.scraper import PropertyListing
from src.sheets_submission import SheetsSubmitter


def test_init_missing_credentials() -> None:
    """Test that missing credentials file raises error."""
    with pytest.raises(FileNotFoundError, match="Credentials file not found"):
        SheetsSubmitter(credentials_path="nonexistent.json")


def test_submit_empty_listings(caplog: LogCaptureFixture) -> None:
    """Test submitting empty list logs warning."""
    with patch("src.sheets_submission.Path.exists", return_value=True), patch("src.sheets_submission.Credentials"), patch("src.sheets_submission.gspread"):
        submitter = SheetsSubmitter()

        with caplog.at_level(logging.WARNING):
            submitter.submit_listings(listings=[], sheet_url="https://example.com", worksheet_name="Sheet1")

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "No listings to submit" in caplog.records[0].message


@patch("src.sheets_submission.gspread")
@patch("src.sheets_submission.Credentials")
def test_row_formatting(mock_creds: MagicMock, mock_gspread: MagicMock) -> None:  # noqa: ARG001
    """Test that listings are formatted into correct row structure."""
    mock_client = MagicMock()
    mock_gspread.authorize.return_value = mock_client

    listing = PropertyListing(address="123 Main St", price="$2000", median_price="2000", link="https://example.com")

    with patch("src.sheets_submission.Path.exists", return_value=True):
        submitter = SheetsSubmitter()

    submitter.submit_listings(listings=[listing], sheet_url="https://example.com", worksheet_name="Sheet1")

    worksheet = mock_client.open_by_url().worksheet()
    worksheet.append_rows.assert_called_once()

    rows = worksheet.append_rows.call_args[0][0]
    assert len(rows) == 1
    assert len(rows[0]) == 6  # timestamp, date, address, price, median_price, link
