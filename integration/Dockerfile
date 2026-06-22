FROM python:3.14-alpine3.23@sha256:02da11a8d221ca167aa07de20b3cd7104c1f01227f4b02b1fa13cf6517280a81

RUN mkdir /app
WORKDIR /app

COPY config.py config.py
COPY requirements.txt requirements.txt
COPY test_end_to_end.py test_end_to_end.py

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "-m", "pytest", "."]
