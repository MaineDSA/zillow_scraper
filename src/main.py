import logging
import time

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)


class ZillowRequestParams:
    """Store constants for Zillow requests."""

    CLONE_URL = "https://appbrewery.github.io/Zillow-Clone/"
    HEADER = {  # noqa: RUF012
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Priority": "u=1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        # "Sec-Fetch-User": "?1",
        "Sec-GPC": "1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0",
    }


class GoogleFormConstants:
    """Store constants for Google Form requests."""

    FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScMTs3orJel4v1R9Y2uw5cDErSjS9CbE2vO00dpXNU6RsdWXA/viewform?usp=header"
    ADDRESS_INPUT_XPATH = (By.XPATH, '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[1]/div/div/div[2]/div/div[1]/div/div[1]/input')
    PRICE_INPUT_XPATH = (By.XPATH, '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[2]/div/div/div[2]/div/div[1]/div/div[1]/input')
    LINK_INPUT_XPATH = (By.XPATH, '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[3]/div/div/div[2]/div/div[1]/div/div[1]/input')


class ZillowHomeFinder:
    """Instantiate object with methods to scrape content from Zillow."""

    def __init__(self, soup: BeautifulSoup) -> None:
        self.soup = soup

    def get_address(self) -> list[str]:
        address_elements = soup.find_all("address", {"data-test": "property-card-addr"})
        return [addr.get_text(strip=True).replace("|", "") for addr in address_elements]

    def get_prices(self) -> list[str]:
        price_elements = soup.find_all("span", class_="PropertyCardWrapper__StyledPriceLine")
        return [price.get_text(strip=True).replace("+/mo", "").replace("/mo", "").replace("+ 1 bd", "").replace("+ 1bd", "") for price in price_elements]

    def get_links(self) -> list[str]:
        address_links = soup.find_all("a", {"data-test": "property-card-link"})
        return [link["href"] for link in address_links]

    def upload_data(self, url: str = GoogleFormConstants.FORM_URL) -> None:
        address_list = self.get_address()
        price_list = self.get_prices()
        link_list = self.get_links()

        driver.get(url)
        driver.maximize_window()
        time.sleep(1)

        try:
            address_input = wait.until(expected_conditions.presence_of_element_located(GoogleFormConstants.ADDRESS_INPUT_XPATH))
            price_input = wait.until(expected_conditions.presence_of_element_located(GoogleFormConstants.PRICE_INPUT_XPATH))
            link_input = wait.until(expected_conditions.presence_of_element_located(GoogleFormConstants.LINK_INPUT_XPATH))
            for address, price, link in zip(address_list, price_list, link_list, strict=False):
                address_input.send_keys(address)
                price_input.send_keys(price)
                link_input.send_keys(link)
                link_input.send_keys(Keys.ENTER)
                time.sleep(1)
                address_input.clear()
                price_input.clear()
                link_input.clear()
        except (NoSuchElementException, TimeoutException) as e:
            err_msg = f"Error while uploading data: {e}"
            logger.error(err_msg)

        finally:
            driver.quit()


if __name__ == "__main__":
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option(name="detach", value=True)
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 10)
    response = requests.get(url=ZillowRequestParams.CLONE_URL, headers=ZillowRequestParams.HEADER)
    soup = BeautifulSoup(response.text, "html.parser")
    bot = ZillowHomeFinder(soup)

    bot.upload_data()
