"""Form submission handling for property listings."""

import logging
from random import SystemRandom

from patchright.async_api import Page
from patchright.async_api import TimeoutError as PlaywrightTimeoutError
from tqdm import tqdm

from src.constants import GoogleFormConstants
from src.scraper import PropertyListing

logger = logging.getLogger(__name__)
cryptogen = SystemRandom()


async def _submit_single_listing(page: Page, url: str, listing: PropertyListing) -> None:
    """Submit a single listing to the Google Form."""
    await page.goto(url)
    await page.wait_for_timeout(cryptogen.randint(1000, 3000))

    await page.fill(GoogleFormConstants.ADDRESS_INPUT_XPATH, listing.address)
    await page.fill(GoogleFormConstants.PRICE_INPUT_XPATH, listing.price)
    await page.fill(GoogleFormConstants.LINK_INPUT_XPATH, listing.link)

    await page.click(GoogleFormConstants.SUBMIT_BUTTON_XPATH)

    try:
        await page.wait_for_selector('div:has-text("Your response has been recorded")', timeout=5000)
    except PlaywrightTimeoutError as e:
        error_msg = f"Form submission confirmation not received for {listing.address}"
        raise PlaywrightTimeoutError(error_msg) from e

    await page.wait_for_timeout(cryptogen.randint(1000, 1500))


async def submit_listings(page: Page, form_url: str, listings: list[PropertyListing]) -> None:
    """Submit all listings to the Google Form with progress tracking."""
    if not listings:
        logger.warning("No listings to submit")
        return

    successful = 0
    failed = 0

    for listing in tqdm(listings, desc="Submitting listings", unit="listing"):
        try:
            await _submit_single_listing(page, form_url, listing)
            successful += 1
        except PlaywrightTimeoutError as e:
            logger.error("Failed to submit listing: %s - Error: %s", listing.address, e)
            failed += 1

    logger.info("Submission complete: %s successful, %s failed", successful, failed)
