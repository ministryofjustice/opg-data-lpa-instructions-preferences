FROM ubuntu:24.04@sha256:db6914f1ac0c566f57857641e2214e3f3e453cb340cc2c890ed6c2b7b81b8a00

RUN mkdir /app
WORKDIR /app


RUN apt-get update -y && \
    apt-get install -y python3 python3-pip tesseract-ocr libtesseract-dev libleptonica-dev pkg-config poppler-utils libgl1

COPY requirements.txt /app/requirements.txt
COPY form-tools/requirements-dev.txt /app/requirements-dev.txt
RUN pip install --break-system-packages -r requirements.txt && \
    pip install --break-system-packages -r requirements-dev.txt

ENTRYPOINT ["pytest", "tests/", "-vv"]
