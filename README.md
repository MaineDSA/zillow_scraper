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

### Python packages

Navigate to the program directory and install with:

    ```shell
    pip install .
    ```

## How to Use

1. Clone the repository
1. Open terminal and navigate to the cloned directory
1. Install python dependencies

    ```shell
    pip install -r .\pyproject.toml
    ```

1. In `src/main.py`, update `FORM_URL` and `FormSelectors` to match your Google Form
1. Run the script:

    ```shell
    python main.py
    ```

The script will open a Chrome window, scrape data from the Zillow clone, and submit each entry into your form.