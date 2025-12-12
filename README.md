[![Python checks](https://github.com/MaineDSA/zillow_scraper/actions/workflows/python.yml/badge.svg)](https://github.com/MaineDSA/zillow_scraper/actions/workflows/python.yml)
[![CodeQL analysis](https://github.com/MaineDSA/zillow_scraper/actions/workflows/codeql.yml/badge.svg)](https://github.com/MaineDSA/zillow_scraper/actions/workflows/codeql.yml)
[![Test coverage](https://raw.githubusercontent.com/MaineDSA/zillow_scraper/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/MaineDSA/zillow_scraper/blob/python-coverage-comment-action-data/htmlcov/index.html)


# Zillow Clone Scraper and Form Auto-Filler

This Python script scrapes apartment listings from a Zillow clone site and optionally submits the address, price, and link of each listing into a Google Form or Google Sheet.

## Features

- Scrapes addresses, prices, and links from listings
- Submits each listing to a Google Form or Google Sheet

## Requirements

- Python 3.11 or higher
- Linux, Windows, macOS

## How to Use

1. Clone the repository
1. Open terminal and navigate to the cloned directory
1. Install python dependencies

    ```shell
    pip install .
    patchright install
    ```

1. Create a folder called `env` in the project directory with one or more files each containing the following contents:

    ```bash
    CONFIG_NAME=<NAME SHOWN WHEN REFERRING TO THIS CONFIG (OPTIONAL)>
    SEARCH_URL=<URL OF THE ZILLOW CLONE TO SCRAPE>
    FORM_URL=<YOUR GOOGLE FORMS URL (OPTIONAL)>
    SHEET_URL=<YOUR GOOGLE SHEETS DOC URL (OPTIONAL)>
    SHEET_NAME=<NAME OF SHEET IN GOOGLE SHEETS DOC TO ADD TO (OPTIONAL)>
    ```

1. If using batch submission to a Google Sheet, add your Google Service Worker authentication file in the project root as ".service_account.json".

1. Run the script:

    ```shell
    python -m src.main
    ```

The script will open a Chrome window, scrape data from each page of the Zillow clone, and submit each entry into your form.
