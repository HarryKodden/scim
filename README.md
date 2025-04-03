# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/HarryKodden/scim/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                              |    Stmts |     Miss |   Cover |   Missing |
|---------------------------------- | -------: | -------: | ------: | --------: |
| code/auth.py                      |       12 |        0 |    100% |           |
| code/data/\_\_init\_\_.py         |       45 |       21 |     53% |44-58, 63-66, 68-71, 73-80, 86-93 |
| code/data/groups.py               |       63 |       13 |     79% |79, 87-95, 105-112 |
| code/data/plugins/\_\_init\_\_.py |       18 |        4 |     78% |21, 24, 27, 30 |
| code/data/plugins/file.py         |       31 |        0 |    100% |           |
| code/data/users.py                |       54 |       12 |     78% |44-48, 55, 79, 87-95 |
| code/filter.py                    |      124 |       30 |     76% |46, 81-98, 111, 121-122, 128, 131, 138, 140, 142, 151, 155, 178-179 |
| code/main.py                      |       34 |        9 |     74% |37-39, 47-50, 75, 79 |
| code/routers/\_\_init\_\_.py      |       76 |       15 |     80% |35-60, 77, 111, 121-122 |
| code/routers/config.py            |        8 |        0 |    100% |           |
| code/routers/groups.py            |       68 |        5 |     93% |134-138, 170, 183-184 |
| code/routers/resource.py          |       20 |        0 |    100% |           |
| code/routers/schema.py            |       21 |        0 |    100% |           |
| code/routers/users.py             |       82 |       15 |     82% |135-137, 167-171, 179, 185-186, 196-204, 216, 228-229 |
| code/schema.py                    |      119 |        6 |     95% |144, 221-222, 247-250 |
| test/conftest.py                  |       34 |       11 |     68% |     31-51 |
| test/test\_auth.py                |        8 |        0 |    100% |           |
| test/test\_config.py              |        3 |        0 |    100% |           |
| test/test\_docs.py                |        3 |        0 |    100% |           |
| test/test\_group.py               |       80 |        0 |    100% |           |
| test/test\_health.py              |        6 |        0 |    100% |           |
| test/test\_resource.py            |       12 |        0 |    100% |           |
| test/test\_schema.py              |       13 |        0 |    100% |           |
| test/test\_user.py                |       60 |        0 |    100% |           |
| test/test\_validation.py          |       10 |        0 |    100% |           |
|                         **TOTAL** | **1004** |  **141** | **86%** |           |


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