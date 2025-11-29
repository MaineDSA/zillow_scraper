"""Main entry point for Zillow scraper."""

import asyncio
import logging

from patchright.async_api import ViewportSize, async_playwright

from .automation import deduplicate_listings, scrape_all_pages, sort_by_newest
from .config import ScraperConfig, load_configs
from .form_submission import submit_listings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def scrape_zillow(config: ScraperConfig) -> None:
    """Launch browser, scrape Zillow listings, and submit to Google Form."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            viewport=ViewportSize({"width": 1280, "height": 768}),
        )
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
        logger.info("Completed config: '%s'", config.config_name)


if __name__ == "__main__":
    main()
