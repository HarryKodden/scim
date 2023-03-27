# scim-sample

## Build the image

```bash
docker build -t scim .
```

## Starting the application

```bash
docker run -p 8000:8000 scim
```

go to your browser and open window at:

```bash
http://localhost:8000
```

## Environment variables

This image uses environment variables for configuration.

| Available variables | Description                                      | Example                                   | Default |
| ------------------- | ------------------------------------------------ | ----------------------------------------- | ------- |
| `LOGLEVEL`          | The application logging level                    | ERROR                                     | INFO    |
| `API_KEY`           | The API key to authenticate with                 | API_KEY=jdjdjdjdehc04                     | secret  |
| `BASE_PATH`         | The base path of all API endpoints               | /api/v2                                   | /       | 
| `DATA_PATH`         | File system path name | /mnt/scim | /tmp    |
| `MONGO_DB`         | Mongo connection string | mongodb://user:password@mongo_host | mongodb://localhost:27017/    |
| `DATABASE_URL`         | SQL Database connection string | postgresql://user:password@postrgres_host:5432/mydb **or** mysql+pymysql://user:password@mysql_host/mydb | sqlite:///scim.sqlite    |

