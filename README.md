# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/HarryKodden/scim/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                              |    Stmts |     Miss |   Cover |   Missing |
|---------------------------------- | -------: | -------: | ------: | --------: |
| code/auth.py                      |       12 |        0 |    100% |           |
| code/data/\_\_init\_\_.py         |       27 |       12 |     56% |26-29, 31-34, 36-39, 41-44 |
| code/data/groups.py               |       42 |        2 |     95% |    46, 51 |
| code/data/plugins/\_\_init\_\_.py |       15 |        5 |     67% |11, 17, 20, 23, 26 |
| code/data/plugins/file.py         |       32 |        0 |    100% |           |
| code/data/users.py                |       55 |       13 |     76% |43-47, 52-54, 84-92 |
| code/filter.py                    |       92 |       38 |     59% |40, 57-76, 81, 89, 91, 93, 98-111, 129-130, 140 |
| code/main.py                      |       34 |        9 |     74% |38-40, 48-51, 76, 80 |
| code/routers/\_\_init\_\_.py      |       59 |       12 |     80% |76, 86-87, 104-116 |
| code/routers/config.py            |        8 |        1 |     88% |        19 |
| code/routers/groups.py            |       56 |       12 |     79% |104-108, 116, 133-146 |
| code/routers/resource.py          |       20 |        1 |     95% |        47 |
| code/routers/schema.py            |       20 |        1 |     95% |        46 |
| code/routers/users.py             |       62 |       27 |     56% |92-96, 104-106, 114, 123-149, 163-176 |
| code/schema.py                    |       88 |        0 |    100% |           |
| test/conftest.py                  |       12 |        0 |    100% |           |
| test/test\_auth.py                |        8 |        0 |    100% |           |
| test/test\_docs.py                |        3 |        0 |    100% |           |
| test/test\_group.py               |       66 |        0 |    100% |           |
| test/test\_health.py              |        6 |        0 |    100% |           |
| test/test\_resource.py            |        9 |        0 |    100% |           |
| test/test\_schema.py              |        9 |        0 |    100% |           |
| test/test\_user.py                |       37 |        0 |    100% |           |
|                         **TOTAL** |  **772** |  **133** | **83%** |           |


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