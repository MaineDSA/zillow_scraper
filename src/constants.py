"""Constants and custom exceptions."""

from typing import ClassVar

CLONE_URL = "https://appbrewery.github.io/Zillow-Clone/"

MIN_WAIT_TIME = 1000
MAX_WAIT_TIME = 3000
MIN_SCROLL_DOWN = 300
MAX_SCROLL_DOWN = 800
MIN_SCROLL_UP = 100
MAX_SCROLL_UP = 300
PROBABILITY_SCROLL_UP = 0.15


class GoogleFormConstants:
    """Constants for Google Form submission."""

    ADDRESS_INPUT_XPATH: ClassVar[str] = 'xpath=//*[@id="mG61Hd"]/div[2]/div/div[2]/div[1]/div/div/div[2]/div/div[1]/div/div[1]/input'
    PRICE_INPUT_XPATH: ClassVar[str] = 'xpath=//*[@id="mG61Hd"]/div[2]/div/div[2]/div[2]/div/div/div[2]/div/div[1]/div/div[1]/input'
    LINK_INPUT_XPATH: ClassVar[str] = 'xpath=//*[@id="mG61Hd"]/div[2]/div/div[2]/div[3]/div/div/div[2]/div/div[1]/div/div[1]/input'
    SUBMIT_BUTTON_XPATH: ClassVar[str] = 'xpath=//*[@id="mG61Hd"]/div[2]/div/div[3]/div/div[1]/div'


class ZillowParseError(Exception):
    """Custom exception for Zillow scraping errors."""
