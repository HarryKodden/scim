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

| Available variables | Description                      | Example               | Default |
| ------------------- | -------------------------------- | --------------------- | ------- |
| `DATA_PATH`         | File system path name            | DATA_PATH=/mnt/scim   | /tmp    |
| `API_KEY`           | The API key to authenticate with | API_KEY=jdjdjdjdehc04 | secret  |
| `LOGLEVEL`          | The application logging level    | ERROR                 | INFO    |
