# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/HarryKodden/scim/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                              |    Stmts |     Miss |   Cover |   Missing |
|---------------------------------- | -------: | -------: | ------: | --------: |
| code/auth.py                      |       12 |        0 |    100% |           |
| code/data/\_\_init\_\_.py         |       29 |       12 |     59% |30-33, 35-38, 40-47, 53-60 |
| code/data/groups.py               |       61 |       12 |     80% |82-90, 100-107 |
| code/data/plugins/\_\_init\_\_.py |       15 |        5 |     67% |11, 17, 20, 23, 26 |
| code/data/plugins/file.py         |       32 |        0 |    100% |           |
| code/data/users.py                |       56 |       11 |     80% |45-49, 56, 86-94 |
| code/filter.py                    |      124 |       32 |     74% |46, 81-98, 111, 115-116, 121-122, 128, 131, 138, 140, 142, 151, 155, 178-179 |
| code/main.py                      |       34 |        5 |     85% |38-40, 76, 80 |
| code/routers/\_\_init\_\_.py      |       76 |       15 |     80% |35-60, 77, 111, 121-122 |
| code/routers/config.py            |        8 |        0 |    100% |           |
| code/routers/groups.py            |       65 |        5 |     92% |125-129, 161, 174-175 |
| code/routers/resource.py          |       20 |        0 |    100% |           |
| code/routers/schema.py            |       20 |        0 |    100% |           |
| code/routers/users.py             |       79 |       15 |     81% |128-130, 157-161, 169, 175-176, 186-194, 206, 218-219 |
| code/schema.py                    |       93 |        0 |    100% |           |
| test/conftest.py                  |       21 |        0 |    100% |           |
| test/test\_auth.py                |        8 |        0 |    100% |           |
| test/test\_config.py              |        3 |        0 |    100% |           |
| test/test\_docs.py                |        3 |        0 |    100% |           |
| test/test\_group.py               |       80 |        0 |    100% |           |
| test/test\_health.py              |        6 |        0 |    100% |           |
| test/test\_resource.py            |       12 |        0 |    100% |           |
| test/test\_schema.py              |       12 |        0 |    100% |           |
| test/test\_user.py                |       60 |        0 |    100% |           |
| test/test\_validation.py          |       10 |        0 |    100% |           |
|                         **TOTAL** |  **939** |  **112** | **88%** |           |


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