"""Main entry point for Zillow scraper."""

import asyncio
import logging

from src.automation import create_browser_context, deduplicate_listings, scrape_all_pages, sort_by_newest
from src.config import ScraperConfig, load_configs
from src.form_submission import submit_listings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def scrape_zillow(config: ScraperConfig) -> None:
    """Launch browser, scrape Zillow listings, and submit to Google Form."""
    browser, context = await create_browser_context()
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

        # Phase 3: Submit to form
        if not unique_listings:
            logger.warning("No listings to submit")
        elif not config.form_url:
            logger.warning("No form URL provided, skipping submission")
        else:
            logger.info("Submitting %s unique listings to Google Form...", len(unique_listings))
            await submit_listings(page, config.form_url, unique_listings)

    finally:
        await browser.close()


def main() -> None:
    """Load configurations and run scraper for each."""
    for config in load_configs():
        logger.info("Processing config: '%s'", config.config_name)
        asyncio.run(scrape_zillow(config))
        logger.debug("Completed config: '%s'", config.config_name)


if __name__ == "__main__":
    main()
