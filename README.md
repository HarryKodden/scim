![CI Workflow](https://github.com/harrykodden/scim-sample/actions/workflows/ci.yml/badge.svg) ![cov](https://raw.githubusercontent.com/HarryKodden/scim-sample/python-coverage-comment-action-data/badge.svg)

# SCIM

## Docker image

Public image available at:
https://hub.docker.com/r/harrykodden/scim

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

## Environment variables

This image uses environment variables for configuration.

| Available variables | Description                           | Example                                                                                                  | Default                       |
| ------------------- | ------------------------------------- | -------------------------------------------------------------------------------------------------------- | ----------------------------- |
| `LOGLEVEL`          | The application logging level         | ERROR                                                                                                    | INFO                          |
| `API_KEY`           | The API key to authenticate with      | mysecret                                                                                                 | secret                        |
| `BASE_PATH`         | The base path of all API endpoints    | /api/v2                                                                                                  | /                             |
| `DATA_PATH`         | File system path name                 | /mnt/scim                                                                                                | /tmp                          |
| `MONGO_DB`          | Mongo connection string               | mongodb://user:password@mongo_host                                                                       | mongodb://localhost:27017/    |
| `DATABASE_URL`      | SQL Database connection string        | postgresql://user:password@postrgres_host:5432/mydb **or** mysql+pymysql://user:password@mysql_host/mydb | sqlite:///scim.sqlite         |
| `JUMPCLOUD_URL`     | The API endpoint for JumpCloud        | https://console.jumpcloud.com                                                                            | https://console.jumpcloud.com |
| `JUMPCLOUD_KEY`     | The API Key for your JumpCloud tenant | _value of API key obtained from JumpCloud_<br /><br />**Mandatory when JUMPCLOUD_URL is set**            | None                          |

## Handling data

The data that is received by this SCIM server can be handled in different ways. Below is an example on how to pick up specific attributes from the received data.

### Example on MySQL

Suppose you have configured a MySQL database via the SQL Plugin configuration. Then your data will be persisted in 2 MySQL database tables **Users** and **Groups**.
The structure of both tables are alike and have only 2 columnns

| id                           | details                                                              |
| ---------------------------- | -------------------------------------------------------------------- |
| unique uuid of this resource | this is a JSON datatype holding the data attributes of this resource |

For example after a provisiong the data for **Users** contains:

| id                                   | details                                                                                                                                                                                                                                                                                                |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 613277a6-aa52-440e-b604-9bbd14343558 | {\"userName\": \"hkodden5\", \"active\": true, \"externalId\": \"44cb3ba1-7a58-49af-961d-9a1253a26181@sram.surf.nl\", \"name\": {\"familyName\": \"Kodden\", \"givenName\": \"Harry\"}, \"displayName\": \"Harry Kodden\", \"emails\": [{\"primary\": true, \"value\": \"harry.kodden@surf.nl\"}] ...} |

Then you would like to retrieve specific values out of the JSON data.
For example, we want to lookup the userName.

```sql
select id, details->'$.userName' as userName from Users where id = '613277a6-aa52-440e-b604-9bbd14343558';
```

will result in:

| id                                   | userName   |
| ------------------------------------ | ---------- |
| 613277a6-aa52-440e-b604-9bbd14343558 | "hkodden5" |
