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

| Available variables | Description                                      | Example                                                       | Default |
| ------------------- | ------------------------------------------------ | ------------------------------------------------------------- | ------- |
| `BASE_PATH`           | The base path of all API endpoints                 |
 '/api/v2' | '/' | 
| `DATA_PATH`         | File system path name or Mongo connection string | DATA_PATH=/mnt/scim <br> DATA_PATH=mongodb://localhost:27017/ | /tmp    |
| `API_KEY`           | The API key to authenticate with                 | API_KEY=jdjdjdjdehc04                                         | secret  |
| `LOGLEVEL`          | The application logging level                    | ERROR                                                         | INFO    |
