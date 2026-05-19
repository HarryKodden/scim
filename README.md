# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/HarryKodden/scim/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                 |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------- | -------: | -------: | ------: | --------: |
| code/auth.py                         |       17 |        0 |    100% |           |
| code/bulk/\_\_init\_\_.py            |        0 |        0 |    100% |           |
| code/bulk/executor.py                |      110 |       11 |     90% |24, 26, 75, 132, 146, 169, 208, 221-222, 237-238 |
| code/data/groups.py                  |       66 |        9 |     86% |57, 83, 90-98, 117 |
| code/data/plugins/\_\_init\_\_.py    |       18 |        4 |     78% |21, 24, 27, 30 |
| code/data/plugins/file.py            |       31 |        0 |    100% |           |
| code/data/users.py                   |       55 |        8 |     85% |49, 78, 85-93 |
| code/events/\_\_init\_\_.py          |       32 |        2 |     94% |    45, 90 |
| code/events/async\_jobs.py           |      159 |       32 |     80% |48, 53-57, 66, 117, 123, 126, 129-130, 136, 167-176, 182-183, 196-199, 227-228, 235-237, 260, 286 |
| code/events/builder.py               |      107 |       15 |     86% |82-84, 87-89, 120-132, 192 |
| code/events/config.py                |       24 |        2 |     92% |    35, 39 |
| code/events/delivery/\_\_init\_\_.py |        2 |        0 |    100% |           |
| code/events/delivery/dispatch.py     |       12 |        0 |    100% |           |
| code/events/delivery/poll.py         |       59 |        1 |     98% |        31 |
| code/events/delivery/push.py         |       36 |        0 |    100% |           |
| code/events/feed\_events.py          |       79 |       13 |     84% |43, 49, 59-66, 79, 81, 95, 97, 109, 124, 139, 149 |
| code/events/feed\_registry.py        |       88 |       18 |     80% |41-54, 83, 90-91, 98-101, 126, 136 |
| code/events/mapping.py               |       15 |        0 |    100% |           |
| code/events/prefer.py                |       17 |        2 |     88% |     28-29 |
| code/events/publisher.py             |       37 |        6 |     84% |67-74, 111-117 |
| code/events/signing.py               |       11 |        0 |    100% |           |
| code/filter.py                       |      197 |       32 |     84% |138-139, 162-165, 201, 217-243, 260-261, 268, 290, 299, 306 |
| code/main.py                         |       41 |        5 |     88% |66-68, 90, 94 |
| code/routers/\_\_init\_\_.py         |      209 |       20 |     90% |67, 106-107, 178, 237, 243, 248, 254-255, 284, 304, 324-325, 356, 360-362, 377-378, 381 |
| code/routers/async\_results.py       |       11 |        0 |    100% |           |
| code/routers/bulk.py                 |       29 |        3 |     90% | 35, 63-64 |
| code/routers/config.py               |       12 |        0 |    100% |           |
| code/routers/feeds.py                |       31 |        0 |    100% |           |
| code/routers/groups.py               |       81 |       11 |     86% |134-138, 146, 154-155, 173, 177, 202-205 |
| code/routers/resource.py             |       20 |        0 |    100% |           |
| code/routers/schema.py               |       18 |        0 |    100% |           |
| code/routers/users.py                |       99 |       17 |     83% |127-129, 158, 164-168, 176, 185-186, 196-205, 226, 252-253 |
| code/schema.py                       |      157 |       10 |     94% |68-69, 98, 230, 245, 368-369, 397-400 |
| code/scim\_errors.py                 |       58 |        6 |     90% |42, 109, 119-125, 146 |
| code/services/\_\_init\_\_.py        |        0 |        0 |    100% |           |
| code/services/groups.py              |       83 |       16 |     81% |36-37, 53-54, 73-74, 79, 84, 92-93, 105, 108, 112-113, 137-138 |
| code/services/users.py               |      101 |       14 |     86% |41, 55-56, 75-76, 89, 97-98, 117-118, 139, 145-146, 156 |
| code/versioning.py                   |       69 |       14 |     80% |21-24, 30, 36, 43-45, 53, 60, 85, 88, 101 |
| test/conftest.py                     |       56 |       17 |     70% |31-51, 67-68, 73-74, 79-80 |
| test/test\_async\_requests.py        |      111 |        0 |    100% |           |
| test/test\_auth.py                   |        8 |        0 |    100% |           |
| test/test\_bulk.py                   |      104 |        3 |     97% |14-15, 196 |
| test/test\_config.py                 |       16 |        0 |    100% |           |
| test/test\_docs.py                   |        3 |        0 |    100% |           |
| test/test\_events.py                 |       70 |        0 |    100% |           |
| test/test\_events\_config.py         |       41 |        0 |    100% |           |
| test/test\_feeds.py                  |      101 |        0 |    100% |           |
| test/test\_filter.py                 |      242 |        0 |    100% |           |
| test/test\_group.py                  |      104 |        0 |    100% |           |
| test/test\_health.py                 |        6 |        0 |    100% |           |
| test/test\_phase3.py                 |       81 |        0 |    100% |           |
| test/test\_poll\_unit.py             |       47 |        0 |    100% |           |
| test/test\_push.py                   |       58 |        0 |    100% |           |
| test/test\_resource.py               |       22 |        0 |    100% |           |
| test/test\_routers\_utils.py         |       57 |        0 |    100% |           |
| test/test\_schema.py                 |       57 |        0 |    100% |           |
| test/test\_scim\_errors.py           |       76 |        0 |    100% |           |
| test/test\_services.py               |      113 |        0 |    100% |           |
| test/test\_user.py                   |       67 |        0 |    100% |           |
| test/test\_validation.py             |       10 |        0 |    100% |           |
| **TOTAL**                            | **3641** |  **291** | **92%** |           |


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