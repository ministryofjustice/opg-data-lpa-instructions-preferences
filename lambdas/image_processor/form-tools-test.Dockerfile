FROM ubuntu:24.04

RUN mkdir /app
WORKDIR /app


RUN apt-get update -y && \
    apt-get install -y python3 python3-pip tesseract-ocr libtesseract-dev libleptonica-dev pkg-config poppler-utils libgl1

COPY requirements.txt /app/requirements.txt
COPY form-tools/requirements-dev.txt /app/requirements-dev.txt
RUN pip install --break-system-packages -r requirements.txt && \
    pip install --break-system-packages -r requirements-dev.txt

ENTRYPOINT ["pytest", "tests/", "-vv"]
