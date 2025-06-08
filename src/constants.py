from typing import ClassVar


class ZillowURLs:
    """Constants for Zillow request handling."""

    ZILLOW_URL: ClassVar[str] = "https://www.zillow.com/portland-me-04101/rentals/"
    CLONE_URL: ClassVar[str] = "https://appbrewery.github.io/Zillow-Clone/"


class GoogleFormConstants:
    """Constants for Google Form submission."""

    ADDRESS_INPUT_XPATH: ClassVar[str] = 'xpath=//*[@id="mG61Hd"]/div[2]/div/div[2]/div[1]/div/div/div[2]/div/div[1]/div/div[1]/input'
    PRICE_INPUT_XPATH: ClassVar[str] = 'xpath=//*[@id="mG61Hd"]/div[2]/div/div[2]/div[2]/div/div/div[2]/div/div[1]/div/div[1]/input'
    LINK_INPUT_XPATH: ClassVar[str] = 'xpath=//*[@id="mG61Hd"]/div[2]/div/div[2]/div[3]/div/div/div[2]/div/div[1]/div/div[1]/input'
    SUBMIT_BUTTON_XPATH: ClassVar[str] = 'xpath=//*[@id="mG61Hd"]/div[2]/div/div[3]/div/div[1]/div'
