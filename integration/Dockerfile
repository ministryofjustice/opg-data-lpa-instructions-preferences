FROM python:3.14-alpine3.23@sha256:54d4310f06b22ce510cf058653729b257e161e0e13e01bf934553bee6550b9a7

RUN mkdir /app
WORKDIR /app

COPY config.py config.py
COPY requirements.txt requirements.txt
COPY test_end_to_end.py test_end_to_end.py

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "-m", "pytest", "."]
