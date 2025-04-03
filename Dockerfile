# Pull base image
FROM python:3.10

# Set environment varibles
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install pipenv

COPY Pipfile .

RUN pipenv lock
RUN pipenv install --system -d

COPY . /app

WORKDIR /app/code

EXPOSE 8000

CMD ["uvicorn", "code.main:app", "--host", "0.0.0.0"] 
