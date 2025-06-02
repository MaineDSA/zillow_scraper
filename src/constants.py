from typing import ClassVar


class ZillowURLs:
    """Constants for Zillow request handling."""

    ZILLOW_URL: ClassVar[str] = "https://www.zillow.com/brunswick-me-04011/rentals/"
    CLONE_URL: ClassVar[str] = "https://appbrewery.github.io/Zillow-Clone/"


class GoogleFormConstants:
    """Constants for Google Form submission."""

    FORM_URL: ClassVar[str] = "https://docs.google.com/forms/d/e/1FAIpQLSfYrPaEL7FXI_wGYiQLUYLuqTijKaE4ZPQTL2LLTGNy6m_cYg/viewform"
    ADDRESS_INPUT_XPATH: ClassVar[str] = 'xpath=//*[@id="mG61Hd"]/div[2]/div/div[2]/div[1]/div/div/div[2]/div/div[1]/div/div[1]/input'
    PRICE_INPUT_XPATH: ClassVar[str] = 'xpath=//*[@id="mG61Hd"]/div[2]/div/div[2]/div[2]/div/div/div[2]/div/div[1]/div/div[1]/input'
    LINK_INPUT_XPATH: ClassVar[str] = 'xpath=//*[@id="mG61Hd"]/div[2]/div/div[2]/div[3]/div/div/div[2]/div/div[1]/div/div[1]/input'
    SUBMIT_BUTTON_XPATH: ClassVar[str] = 'xpath=//*[@id="mG61Hd"]/div[2]/div/div[3]/div/div[1]/div'
