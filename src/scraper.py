import logging
from random import SystemRandom

from bs4 import BeautifulSoup, Tag
from patchright.async_api import Page
from tqdm import tqdm

from src.constants import GoogleFormConstants
from src.exceptions import ZillowParseError
from src.form_submission import _submit_form
from src.parsers import _parse_zillow_card

logger = logging.getLogger(__name__)
cryptogen = SystemRandom()


class ZillowHomeFinder:
    """Scrape property data from a Zillow soup object."""

    def __init__(self, soup: BeautifulSoup) -> None:
        self.cards: list[Tag] = []
        self.addresses: list[str] = []
        self.prices: list[str] = []
        self.links: list[str] = []

        self.cards = soup.find_all("article", attrs={"data-test": "property-card"})
        if not self.cards:
            err = "No property cards found."
            raise ZillowParseError(err)

        msg = f"Found {len(self.cards)} property cards to parse"
        logger.info(msg)

        for i, card in enumerate(self.cards):
            try:
                card_results = _parse_zillow_card(card)
                msg = f"Card {i + 1}: Found {len(card_results)} entries"
                logger.info(msg)

                for address, price, link in card_results:
                    self.addresses.append(address)
                    self.prices.append(price)
                    self.links.append(link)

            except ZillowParseError as e:
                err = f"Skipping card {i + 1} due to parse error: {e}"
                logger.error(err)

    async def upload_data(self, page: Page, url: str = GoogleFormConstants.FORM_URL) -> None:
        for address, price, link in tqdm(zip(self.addresses, self.prices, self.links, strict=False), total=len(self.prices), unit="entry"):
            await _submit_form(page, url, address, price, link)
