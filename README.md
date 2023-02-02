# scim-sample

## Build the image

```bash
docker build -t scim .
```

## Starting the application

```bash
docker run -ti -p 8000:8000 sample
```

go to your browser and open window at:

```bash
http://localhost:8000/apidoc
```

## Environment variables

This image uses environment variables for configuration.

| Available variables | Description                      | Example               | Default |
| ------------------- | -------------------------------- | --------------------- | ------- |
| `DATA_PATH`         | File system path name            | DATA_PATH=/mnt/scim   | /tmp    |
| `API_KEY`           | The API key to authenticate with | API_KEY=jdjdjdjdehc04 | secret  |
| `LOGLEVEL`          | The application logging level    | ERROR                 | INFO    |
