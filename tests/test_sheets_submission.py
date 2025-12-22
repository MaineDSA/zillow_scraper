"""Additional test cases for SheetsSubmitter."""

from collections.abc import Generator
from datetime import UTC, date
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

import gspread
import pytest

from src.scraper import PropertyListing
from src.sheets_submission import SheetsSubmitter


class TestSheetsSubmitter:
    """Tests for Google Sheets submission functionality."""

    @pytest.fixture
    def submitter(self) -> Generator[SheetsSubmitter, None, None]:
        """Create a SheetsSubmitter instance with mocked credentials."""
        with (
            patch("src.sheets_submission.Path.exists", return_value=True),
            patch("src.sheets_submission.Credentials.from_service_account_file"),
            patch("src.sheets_submission.gspread.authorize") as mock_authorize,
        ):
            mock_client = MagicMock()
            mock_authorize.return_value = mock_client
            submitter = SheetsSubmitter()
            yield submitter

    @pytest.fixture
    def sample_listings(self) -> list[PropertyListing]:
        """Sample property listings for testing."""
        return [
            PropertyListing("123 Main St", "$1,000", "1000", "http://example.com/1"),
            PropertyListing("456 Oak Ave", "$1,500", "1500", "http://example.com/2"),
        ]

    def test_init_missing_credentials_file(self) -> None:
        """Test initialization fails when credentials file is missing."""
        with patch("src.sheets_submission.Path.exists", return_value=False), pytest.raises(FileNotFoundError, match="Credentials file not found"):
            SheetsSubmitter("missing_file.json")

    @pytest.mark.parametrize(
        "custom_path",
        [
            "custom/path/creds.json",
            Path("custom/path/creds.json"),
        ],
    )
    def test_init_with_custom_path(self, custom_path: Path | str) -> None:
        """Test initialization with custom credentials path."""
        with (
            patch("src.sheets_submission.Path.exists", return_value=True),
            patch("src.sheets_submission.Credentials.from_service_account_file"),
            patch("src.sheets_submission.gspread.authorize"),
        ):
            submitter = SheetsSubmitter(custom_path)
            assert submitter.credentials_path == Path(custom_path)

    def test_submit_listings_row_format(self, submitter: SheetsSubmitter, sample_listings: list[PropertyListing]) -> None:
        """Test that rows are formatted correctly."""
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_worksheet
        cast("MagicMock", submitter.client.open_by_url).return_value = mock_sheet

        with patch("src.sheets_submission.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.month = 12
            mock_now.day = 21
            mock_now.year = 2025
            mock_now.hour = 14
            mock_now.minute = 30
            mock_now.second = 45
            mock_now.date.return_value = date(2025, 12, 21)
            mock_datetime.datetime.now.return_value = mock_now
            mock_datetime.UTC = UTC

            submitter.submit_listings(listings=sample_listings, sheet_url="http://example.com", append=True)

            call_args = mock_worksheet.append_rows.call_args
            rows: list[list[Any]] = call_args[0][0]

            # Check first row format
            assert rows[0][0] == "12/21/2025 14:30:45"  # timestamp
            assert rows[0][1] == "2025-12-21"  # date
            assert rows[0][2] == "123 Main St"  # address
            assert rows[0][3] == "$1,000"  # price
            assert rows[0][4] == "1000"  # median_price
            assert rows[0][5] == "http://example.com/1"  # link

            # Check number of rows
            assert len(rows) == 2

    @pytest.mark.parametrize(
        "exception_type",
        [
            gspread.exceptions.WorksheetNotFound,
            gspread.exceptions.SpreadsheetNotFound,
            gspread.GSpreadException,
        ],
    )
    def test_submit_listings_error_handling(self, submitter: SheetsSubmitter, sample_listings: list[PropertyListing], exception_type: type[Exception]) -> None:
        """Test error handling for various gspread exceptions."""
        cast("MagicMock", submitter.client.open_by_url).side_effect = exception_type

        with pytest.raises(exception_type):
            submitter.submit_listings(listings=sample_listings, sheet_url="http://example.com", worksheet_name="BadSheet")

    def test_submit_single_listing(self, submitter: SheetsSubmitter) -> None:
        """Test submitting a single listing."""
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_worksheet
        cast("MagicMock", submitter.client.open_by_url).return_value = mock_sheet

        single_listing = [PropertyListing("789 Elm St", "$2,000", "2000", "http://example.com/3")]

        submitter.submit_listings(listings=single_listing, sheet_url="http://example.com", append=True)

        call_args = mock_worksheet.append_rows.call_args
        rows: list[list[Any]] = call_args[0][0]
        assert len(rows) == 1
        assert rows[0][2] == "789 Elm St"


@patch("src.sheets_submission.gspread")
@patch("src.sheets_submission.Credentials")
def test_row_formatting_appended(mock_creds: MagicMock, mock_gspread: MagicMock) -> None:  # noqa: ARG001
    """Test that listings are formatted into correct row structure when appending sheet contents."""
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
    assert rows[0][2] == listing.address
    assert rows[0][3] == listing.price
    assert rows[0][4] == listing.median_price
    assert rows[0][5] == listing.link


@patch("src.sheets_submission.gspread")
@patch("src.sheets_submission.Credentials")
def test_row_formatting_cleared(mock_creds: MagicMock, mock_gspread: MagicMock) -> None:  # noqa: ARG001
    """Test that listings are formatted into correct row structure when replacing sheet contents."""
    mock_client = MagicMock()
    mock_gspread.authorize.return_value = mock_client

    listing = PropertyListing(address="123 Main St", price="$2000", median_price="2000", link="https://example.com")

    with patch("src.sheets_submission.Path.exists", return_value=True):
        submitter = SheetsSubmitter()

    submitter.submit_listings(listings=[listing], sheet_url="https://example.com", worksheet_name="Sheet1", append=False)

    worksheet = mock_client.open_by_url().worksheet()
    worksheet.clear.assert_called_once()
    worksheet.update.assert_called_once()

    rows = worksheet.update.call_args[0][0]
    assert len(rows) == 2
    assert rows[0] == ["Timestamp", "Date", "Address", "Starting Price / Month", "Starting Price / Month (Median of Ranges)", "Link"]
    assert rows[1][2] == listing.address
    assert rows[1][3] == listing.price
    assert rows[1][4] == listing.median_price
    assert rows[1][5] == listing.link
