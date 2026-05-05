FROM python:3.14-alpine3.23@sha256:dd4d2bd5b53d9b25a51da13addf2be586beebd5387e289e798e4083d94ca837a

RUN mkdir /app
WORKDIR /app

COPY config.py config.py
COPY requirements.txt requirements.txt
COPY test_end_to_end.py test_end_to_end.py

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "-m", "pytest", "."]
