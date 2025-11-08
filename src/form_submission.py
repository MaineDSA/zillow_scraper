import logging
from random import SystemRandom

from patchright.async_api import Page
from patchright.async_api import TimeoutError as PlaywrightTimeoutError

from src.constants import GoogleFormConstants

logger = logging.getLogger(__name__)
cryptogen = SystemRandom()


async def _submit_form(page: Page, url: str, address: str, price: str, link: str) -> None:
    await page.goto(url)
    await page.wait_for_timeout(cryptogen.randint(1000, 3000))

    await page.fill(GoogleFormConstants.ADDRESS_INPUT_XPATH, address)
    await page.fill(GoogleFormConstants.PRICE_INPUT_XPATH, price)
    await page.fill(GoogleFormConstants.LINK_INPUT_XPATH, link)

    await page.click(GoogleFormConstants.SUBMIT_BUTTON_XPATH)

    try:
        await page.wait_for_selector('div:has-text("Your response has been recorded")', timeout=5000)
    except PlaywrightTimeoutError as e:
        msg = "Form submission confirmation not received"
        raise PlaywrightTimeoutError(msg) from e

    await page.wait_for_timeout(cryptogen.randint(1000, 1500))
