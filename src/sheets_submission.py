"""Form submission handling for property listings."""

import datetime
import logging
from pathlib import Path
from random import SystemRandom

import gspread
from google.oauth2.service_account import Credentials
from gspread import GSpreadException
from gspread.utils import ValueInputOption

from src.scraper import PropertyListing

logger = logging.getLogger(__name__)
cryptogen = SystemRandom()


class SheetsSubmitter:
    """Handle batch submission of listings to Google Sheets."""

    SCOPES = ("https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive")

    def __init__(self, credentials_path: Path | str = ".service_account.json") -> None:
        """Initialize the sheets client with credentials."""
        self.credentials_path = Path(credentials_path)
        if not self.credentials_path.exists():
            err = f"Credentials file not found at {self.credentials_path}. Please download it from Google Cloud Console."
            raise FileNotFoundError(err)

        creds = Credentials.from_service_account_file(str(self.credentials_path), scopes=self.SCOPES)
        self.client = gspread.authorize(creds)

    def submit_listings(self, *, listings: list[PropertyListing], sheet_url: str, worksheet_name: str = "Sheet1", append: bool = True) -> None:
        """
        Batch submit all listings to Google Sheets.

        Args:
        listings: List of property listings to submit
        sheet_url: Full URL of the Google Sheet
        worksheet_name: Name of the worksheet tab (default: "Sheet1")
        append: If True, append to existing data. If False, clear and overwrite.

        """
        if not listings:
            logger.warning("No listings to submit")
            return

        try:
            sheet = self.client.open_by_url(sheet_url)
            worksheet = sheet.worksheet(worksheet_name)
            now = datetime.datetime.now(tz=datetime.UTC)
            timestamp = f"{now.month}/{now.day}/{now.year} {now.hour}:{now.minute:02d}:{now.second:02d}"
            date = str(now.date())

            rows = [[timestamp, date, listing.address, listing.price, listing.median_price, listing.link] for listing in listings]

            if append:
                worksheet.append_rows(rows, value_input_option=ValueInputOption.raw)
                logger.info("Appended %s listings to sheet", len(rows))
            else:
                headers = [["Timestamp", "Date", "Address", "Starting Price / Month", "Starting Price / Month (Median of Ranges)", "Link"]]
                worksheet.clear()
                worksheet.update(headers + rows, value_input_option=ValueInputOption.raw)
                logger.info("Wrote %s listings to sheet (cleared existing data)", len(rows))

        except gspread.exceptions.WorksheetNotFound:
            logger.error("Worksheet '%s' not found in sheet", worksheet_name)
            raise
        except gspread.exceptions.SpreadsheetNotFound:
            logger.error("Spreadsheet not found. Check the URL and sharing permissions")
            raise
        except GSpreadException as e:
            logger.error("Failed to submit to Google Sheets: %s", e)
            raise
