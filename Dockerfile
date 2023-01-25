# Pull base image
FROM python:3.10

# Set environment varibles
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN pip install pipenv

COPY . /app
RUN pipenv lock
RUN pipenv install --dev --system

EXPOSE 8000