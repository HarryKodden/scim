# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/HarryKodden/scim/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                              |    Stmts |     Miss |   Cover |   Missing |
|---------------------------------- | -------: | -------: | ------: | --------: |
| code/auth.py                      |       12 |        0 |    100% |           |
| code/data/\_\_init\_\_.py         |       21 |        9 |     57% |20-23, 25-28, 30-33 |
| code/data/groups.py               |       42 |        6 |     86% |22, 40-44, 49 |
| code/data/plugins/\_\_init\_\_.py |       15 |        5 |     67% |11, 17, 20, 23, 26 |
| code/data/plugins/file.py         |       32 |        2 |     94% |     47-48 |
| code/data/users.py                |       43 |        8 |     81% |18, 35-39, 44-46 |
| code/filter.py                    |       95 |       41 |     57% |40, 57-76, 81, 89, 91, 93, 98-112, 130-131, 141 |
| code/main.py                      |       30 |        6 |     80% |46, 54-57, 63 |
| code/routers/\_\_init\_\_.py      |       22 |        3 |     86% | 31, 41-42 |
| code/routers/groups.py            |       44 |        8 |     82% |75-76, 84, 94-98, 106, 108-109 |
| code/routers/resource.py          |       20 |        1 |     95% |        47 |
| code/routers/schema.py            |       21 |        1 |     95% |        48 |
| code/routers/users.py             |       45 |       15 |     67% |81-82, 90, 99-125 |
| code/schema.py                    |       86 |        0 |    100% |           |
| test/conftest.py                  |       11 |        0 |    100% |           |
| test/test\_auth.py                |        8 |        0 |    100% |           |
| test/test\_docs.py                |        3 |        0 |    100% |           |
| test/test\_group.py               |       44 |        0 |    100% |           |
| test/test\_resource.py            |       10 |        0 |    100% |           |
| test/test\_schema.py              |       10 |        0 |    100% |           |
| test/test\_user.py                |       37 |        0 |    100% |           |
|                         **TOTAL** |  **651** |  **105** | **84%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/HarryKodden/scim/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/HarryKodden/scim/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/HarryKodden/scim/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/HarryKodden/scim/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FHarryKodden%2Fscim%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/HarryKodden/scim/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.