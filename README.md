![CI Workflow](https://github.com/harrykodden/scim-sample/actions/workflows/ci.yml/badge.svg) ![cov](https://raw.githubusercontent.com/HarryKodden/scim-sample/python-coverage-comment-action-data/badge.svg)

# SCIM

## Docker image

Public image available at:
<https://hub.docker.com/r/harrykodden/scim>

You do not need to build the docker image yourself. You can just pull the prepared image which is available for both **linux/amd** and **linux/arm** architectures.

```bash
docker pull harrykodden/scim
```

## Build the image

Alternatively, you can build the image yourself:

```bash
docker build -t scim .
```

## Starting the application

```bash
docker run -p 8000:8000 harrykodden/scim
```

or if you build it yourself:

```bash
docker run -p 8000:8000 scim
```

This will show like:

```log
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

go to your browser and open window at:

```bash
http://localhost:8000
```

## Data handling options

You have different options to handle the data. The simplest is the the flat files handling. You simply assign a (volume-) path to the location where you want to persist the data.
Other options include SQL and NoSQL database, JumpCloud and forwarding the data to an upstream SCIM Server.

![Data Handling Options](data.png)

The options can be activated by assiging environment variable values, see below.

The plugin methodology makes it very easy to add additional data backends, you simply have to subclass the **Plugin Class** (`code/data/plugins/__init__.py`) and provide logic for the base class methods.

![Plugin](code/data/plugins/__init__.py)

For inspiration on how to do that, please take a look at the provided implementation examples. If you do want to contribute with a nice additional backend, please do not hesitate to submit a Pull Request.

## Environment variables

This image uses environment variables for configuration.

| Available variables | Description                                                                              | Example                                                                                                             | Default                         |
| ------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| `LOGLEVEL`          | The application logging level                                                            | ERROR                                                                                                               | INFO                            |
| `API_KEY`           | The API key to authenticate with                                                         | mysecret                                                                                                            | secret                          |
| `PAGE_SIZE`         | The maximum number of resources returned in 1 response.                                  | 10                                                                                                                  | 100                             |
| `BASE_PATH`         | The base path of all API endpoints                                                       | /api/v2                                                                                                             | /                               |
| `DATA_PATH`         | File system path name                                                                    | /mnt/scim                                                                                                           | /tmp                            |
| `MONGO_DB`          | Mongo connection string                                                                  | mongodb://user:password@mongo_host                                                                                  | mongodb://localhost:27017/      |
| `DATABASE_URL`      | SQL Database connection string                                                           | postgresql://user:password@postrgres_host:5432/mydb<br />**or**<br /> mysql+pymysql://user:password@mysql_host/mydb | sqlite:///scim.sqlite           |
| `JUMPCLOUD_URL`     | The API endpoint for JumpCloud                                                           | <https://console.jumpcloud.com>                                                                                     | <https://console.jumpcloud.com> |
| `JUMPCLOUD_KEY`     | The API Key for your JumpCloud tenant                                                    | **value** of API key obtained from JumpCloud\_<br /><br />**Mandatory when JUMPCLOUD_URL is set**                   | None                            |
| `FORWARD_SCIM_URL`  | Forward SCIM request to upstream SCIM server                                             | <https://example.com/v2/api>                                                                                        | None                            |
| `FORWARD_SCIM_KEY`  | API KEY for **FORWARD_SCIM_URL** scim server. if not provided, **API_KEY** will be used  | <https://example.com/v2/api>                                                                                        | None                            |
| `USER_MAPPING`      | A JSON string that specify how attribute values should be mapped to different attributes | '{"userName": "sram_user_extension.eduPersonUniqueId"}'                                                             | None                            |
| `GROUP_MAPPING`     | A JSON string that specify how attribute values should be mapped to different attributes | '{"id": "displanNameuser_extension.eduPersonUniqueId"}'                                                             | None                            |

## Handling data

The data that is received by this SCIM server can be handled in different ways. Below is an example on how to pick up specific attributes from the received data.

### Example on MySQL

Suppose you have configured a MySQL database via the SQL Plugin configuration. Then your data will be persisted in 2 MySQL database tables **Users** and **Groups**.
The structure of both tables are alike and have only 2 columnns

| id                           | details                                                              |
| ---------------------------- | -------------------------------------------------------------------- |
| unique uuid of this resource | this is a JSON datatype holding the data attributes of this resource |

For example after a provisiong the data for **Users** contains:

| id                                   | details                                                                                                                                                                                                                                                                                                  |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 613277a6-aa52-440e-b604-9bbd14343558 | {\"userName\": \"hkodden5\", \"active\": true, \"externalId\": \"<44cb3ba1-7a58-49af-961d-9a1253a26181@sram.surf.nl>\", \"name\": {\"familyName\": \"Kodden\", \"givenName\": \"Harry\"}, \"displayName\": \"Harry Kodden\", \"emails\": [{\"primary\": true, \"value\": \"harry.kodden@surf.nl\"}] ...} |

Then you would like to retrieve specific values out of the JSON data.
For example, we want to lookup the userName.

```sql
select id, details->'$.userName' as userName from Users where id = '613277a6-aa52-440e-b604-9bbd14343558';
```

will result in:

| id                                   | userName   |
| ------------------------------------ | ---------- |
| 613277a6-aa52-440e-b604-9bbd14343558 | "hkodden5" |
