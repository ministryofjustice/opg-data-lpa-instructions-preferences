FROM python:3.14-alpine3.23@sha256:6f873e340e6786787a632c919ecfb1d2301eb33ccfbe9f0d0add16cbc0892116

RUN mkdir /app
WORKDIR /app

COPY config.py config.py
COPY requirements.txt requirements.txt
COPY test_end_to_end.py test_end_to_end.py

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "-m", "pytest", "."]
