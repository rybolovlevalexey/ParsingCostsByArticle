FROM python:3.12

RUN mkdir /fastapi_app
WORKDIR /fastapi_app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFED 1

COPY requirements.txt requirements.txt

WORKDIR /

RUN pip install -r requirements.txt

COPY . .

CMD gunicorn main:app --bind=0.0.0.0:8000
