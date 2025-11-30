# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/MaineDSA/zillow_scraper/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                    |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------ | -------: | -------: | -------: | -------: | ------: | --------: |
| src/\_\_init\_\_.py     |        0 |        0 |        0 |        0 |    100% |           |
| src/automation.py       |      113 |       77 |       12 |        0 |     32% |21-27, 35-36, 41-45, 58-65, 70-79, 84-92, 97-132, 141-168, 173-187, 206-223 |
| src/config.py           |       27 |        1 |        6 |        1 |     94% |        28 |
| src/constants.py        |       10 |        0 |        0 |        0 |    100% |           |
| src/form\_submission.py |       33 |       20 |        0 |        0 |     39% |19-34, 43-52 |
| src/main.py             |       22 |       13 |        0 |        0 |     41% |     18-47 |
| src/scraper.py          |      160 |        8 |       60 |        9 |     92% |51, 135, 148, 154, 158, 178->176, 188->193, 197, 212-213 |
|               **TOTAL** |  **365** |  **119** |   **78** |   **10** | **69%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/MaineDSA/zillow_scraper/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/MaineDSA/zillow_scraper/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/MaineDSA/zillow_scraper/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/MaineDSA/zillow_scraper/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FMaineDSA%2Fzillow_scraper%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/MaineDSA/zillow_scraper/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.