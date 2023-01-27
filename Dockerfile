# Pull base image
FROM python:3.10

# Set environment varibles
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

RUN pip install pipenv

COPY . /code
RUN pipenv lock
RUN pipenv install --dev --system

VOLUME [ "/data" ]

EXPOSE 8000