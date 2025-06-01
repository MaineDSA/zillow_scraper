[![Python checks](https://github.com/MaineDSA/zillow_scraper/actions/workflows/python.yml/badge.svg)](https://github.com/MaineDSA/zillow_scraper/actions/workflows/python.yml)
[![CodeQL analysis](https://github.com/MaineDSA/zillow_scraper/actions/workflows/codeql.yml/badge.svg)](https://github.com/MaineDSA/zillow_scraper/actions/workflows/codeql.yml)
[![Test coverage](https://raw.githubusercontent.com/MaineDSA/zillow_scraper/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/MaineDSA/zillow_scraper/blob/python-coverage-comment-action-data/htmlcov/index.html)


# Zillow Clone Scraper and Form Auto-Filler

This Python script scrapes apartment listings from a Zillow clone site and automatically submits the address, price, and link of each listing into a Google Form.
The responses are stored in a connected Google Spreadsheet for easy tracking.

## Features

- Scrapes addresses, prices, and links from listings
- Submits each listing to a Google Form
- Data is saved into a linked Google Sheet
- Browser closes automatically when done

## Requirements

- Python 3.11 or higher
- Chrome and ChromeDriver installed

## How to Use

1. Clone the repository
1. Open terminal and navigate to the cloned directory
1. Install python dependencies

    ```shell
    pip install -r .\pyproject.toml
    playwright install
    ```

1. In `src/main.py`, update `GoogleFormConstants.FORM_URL` to match your Google Form
1. Ensure that `GoogleFormConstants.ADDRESS_INPUT_XPATH`, `GoogleFormConstants.PRICE_INPUT_XPATH`, `GoogleFormConstants.LINK_INPUT_XPATH`, and `GoogleFormConstants.SUBMIT_BUTTON_XPATH` match your Google Form.
1. Run the script:

    ```shell
    python main.py
    ```

The script will open a Chrome window, scrape data from the Zillow clone, and submit each entry into your form.
