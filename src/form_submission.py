import logging
from random import SystemRandom

from patchright.async_api import Page

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
    await page.wait_for_timeout(cryptogen.randint(1000, 3000))
