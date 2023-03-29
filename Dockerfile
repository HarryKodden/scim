# Pull base image
ARG BUILDPLATFORM

FROM --platform=$BUILDPLATFORM python:3.10

# Set environment varibles
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

RUN pip install pipenv

COPY code .
COPY Pipfile .

RUN pipenv lock
RUN pipenv install --system

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0"] 