# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/MaineDSA/zillow_scraper/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                      |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|-------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| src/\_\_init\_\_.py       |        0 |        0 |        0 |        0 |    100% |           |
| src/automation.py         |      138 |       93 |       14 |        0 |     32% |32-44, 51-60, 68-69, 74-78, 91, 105-117, 122-130, 135-143, 148-183, 192-219, 224-244, 263-285 |
| src/config.py             |       48 |        3 |       10 |        1 |     93% | 42, 82-84 |
| src/constants.py          |       15 |        0 |        0 |        0 |    100% |           |
| src/form\_submission.py   |       33 |        0 |        0 |        0 |    100% |           |
| src/main.py               |       32 |       19 |        0 |        0 |     41% |20-34, 39-54, 61-62 |
| src/scraper.py            |      166 |        0 |       56 |        0 |    100% |           |
| src/sheets\_submission.py |       41 |        1 |        4 |        0 |     98% |        47 |
| **TOTAL**                 |  **473** |  **116** |   **84** |    **1** | **77%** |           |


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