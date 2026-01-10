"""Main entry point for Zillow scraper."""

import asyncio
import logging

from src.automation import deduplicate_listings, get_browser_page, scrape_all_pages, simulate_human_behavior, sort_by_newest
from src.config import Config, SubmissionType, load_configs
from src.form_submission import submit_listings
from src.scraper import PropertyListing
from src.sheets_submission import SheetsSubmitter

logging.basicConfig(level=logging.INFO, format="%(levelname)s:zillow_scraper:%(name)s:%(message)s")
logger = logging.getLogger(__name__)


async def scrape_listings(config: Config) -> list[PropertyListing]:
    """Scrape and deduplicate listings from Zillow."""
    async with get_browser_page() as page:
        logger.info("Loading search URL: %s...", config.search_url)

        await page.goto(config.search_url)
        await simulate_human_behavior(page)
        if await page.get_by_text("Press & Hold").count() > 0:
            error_msg = "CAPTCHA detected, cannot continue."
            raise BaseException(error_msg)

        logger.info("Scraping all listings...")
        await sort_by_newest(page)
        all_listings = await scrape_all_pages(page)

        logger.info("Deduplicating %s listings...", len(all_listings))
        return deduplicate_listings(all_listings)


async def submit_listings_to_destination(config: Config, listings: list[PropertyListing]) -> None:
    """Submit listings based on configuration."""
    if not listings:
        logger.warning("No listings to submit")
        return

    if config.submission_type == SubmissionType.SHEET and isinstance(config.sheet_url, str):
        logger.info("Submitting %s listings to Google Sheets...", len(listings))
        submitter = SheetsSubmitter()
        submitter.submit_listings(
            listings=listings,
            sheet_url=config.sheet_url,
            worksheet_name=config.sheet_name,
        )
    elif config.submission_type == SubmissionType.FORM and isinstance(config.form_url, str):
        logger.info("Submitting %s listings to Google Form...", len(listings))
        async with get_browser_page() as page:
            await submit_listings(page, config.form_url, listings)
    else:
        logger.warning("No submission destination configured")


async def scrape_and_submit(config: Config) -> None:
    """Orchestrate scraping and submission workflow."""
    listings = await scrape_listings(config)
    await submit_listings_to_destination(config, listings)


def main() -> None:
    """Load configurations and run scraper for each."""
    configs = load_configs()
    for config in configs:
        logger.info("Processing config: '%s'", config.config_name)
        asyncio.run(scrape_and_submit(config))
        logger.debug("Completed config: '%s'", config.config_name)


if __name__ == "__main__":
    main()
