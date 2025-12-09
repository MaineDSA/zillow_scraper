"""Main entry point for Zillow scraper."""

import asyncio
import logging

from src.automation import create_browser_context, deduplicate_listings, scrape_all_pages, sort_by_newest
from src.config import Config, SubmissionType, load_configs
from src.form_submission import submit_listings
from src.sheets_submission import SheetsSubmitter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def scrape_and_submit(config: Config) -> None:
    """Launch browser, scrape Zillow listings, and submit to Google Form or Sheets."""
    playwright, browser, context = await create_browser_context()
    page = await context.new_page()

    try:
        # Phase 1: Scrape all listings
        logger.info("Scraping all listings...")
        await page.goto(config.search_url)
        await sort_by_newest(page)
        all_listings = await scrape_all_pages(page)

        # Phase 2: Deduplicate
        logger.info("Deduplicating %s listings...", len(all_listings))
        unique_listings = deduplicate_listings(all_listings)

        # Phase 3: Submit based on configuration
        if not unique_listings:
            logger.warning("No listings to submit")
        elif config.submission_type == SubmissionType.SHEET:
            logger.info("Submitting %s unique listings to Google Sheets...", len(unique_listings))
            submitter = SheetsSubmitter()
            submitter.submit_listings(
                listings=unique_listings,
                sheet_url=config.sheet_url,  # type: ignore
                worksheet_name=config.sheet_name,
            )
        elif config.submission_type == SubmissionType.FORM:
            logger.info("Submitting %s unique listings to Google Form...", len(unique_listings))
            await submit_listings(page, config.form_url, unique_listings)  # type: ignore
        else:
            logger.warning("No submission destination configured, skipping submission")

    finally:
        await browser.close()
        await playwright.stop()


def main() -> None:
    """Load configurations and run scraper for each."""
    configs = load_configs()
    for config in configs:
        logger.info("Processing config: '%s'", config.config_name)
        asyncio.run(scrape_and_submit(config))
        logger.debug("Completed config: '%s'", config.config_name)


if __name__ == "__main__":
    main()
