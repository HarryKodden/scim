# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/HarryKodden/scim/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                              |    Stmts |     Miss |   Cover |   Missing |
|---------------------------------- | -------: | -------: | ------: | --------: |
| code/auth.py                      |       17 |        0 |    100% |           |
| code/data/\_\_init\_\_.py         |       54 |       24 |     56% |51-65, 70-73, 75-78, 80-87, 93-100, 106-116 |
| code/data/groups.py               |       64 |       13 |     80% |82, 88-96, 108-115 |
| code/data/plugins/\_\_init\_\_.py |       18 |        4 |     78% |21, 24, 27, 30 |
| code/data/plugins/file.py         |       31 |        0 |    100% |           |
| code/data/users.py                |       53 |        8 |     85% |48, 77, 83-91 |
| code/filter.py                    |      197 |       32 |     84% |138-139, 162-165, 201, 217-243, 260-261, 268, 290, 299, 306 |
| code/main.py                      |       43 |        9 |     79% |61-63, 71-74, 99, 103 |
| code/routers/\_\_init\_\_.py      |      107 |       45 |     58% |7-8, 38-67, 84, 118, 128-129, 150-153, 159-194, 202 |
| code/routers/config.py            |        9 |        0 |    100% |           |
| code/routers/groups.py            |       70 |        6 |     91% |135-139, 171, 174, 190-191 |
| code/routers/resource.py          |       20 |        0 |    100% |           |
| code/routers/schema.py            |       18 |        0 |    100% |           |
| code/routers/users.py             |       83 |       16 |     81% |134-136, 166-170, 178, 184-185, 195-203, 215, 218, 233-234 |
| code/schema.py                    |      108 |        7 |     94% |132, 147, 264-265, 290-293 |
| test/conftest.py                  |       34 |       11 |     68% |     31-51 |
| test/test\_auth.py                |        8 |        0 |    100% |           |
| test/test\_config.py              |        3 |        0 |    100% |           |
| test/test\_docs.py                |        3 |        0 |    100% |           |
| test/test\_filter.py              |      242 |        0 |    100% |           |
| test/test\_group.py               |       80 |        0 |    100% |           |
| test/test\_health.py              |        6 |        0 |    100% |           |
| test/test\_resource.py            |       12 |        0 |    100% |           |
| test/test\_schema.py              |       33 |        0 |    100% |           |
| test/test\_user.py                |       60 |        0 |    100% |           |
| test/test\_validation.py          |       10 |        0 |    100% |           |
| **TOTAL**                         | **1383** |  **175** | **87%** |           |


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