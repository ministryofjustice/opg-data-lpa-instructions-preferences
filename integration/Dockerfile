FROM python:3.14-alpine3.23@sha256:5a824eb82cc75361f98611f3cfc5091ea33f10a6ccea4d4ebdabbc523b9a1614

RUN mkdir /app
WORKDIR /app

COPY config.py config.py
COPY requirements.txt requirements.txt
COPY test_end_to_end.py test_end_to_end.py

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "-m", "pytest", "."]
