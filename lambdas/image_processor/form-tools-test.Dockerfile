FROM ubuntu:24.04@sha256:c4a8d5503dfb2a3eb8ab5f807da5bc69a85730fb49b5cfca2330194ebcc41c7b

RUN mkdir /app
WORKDIR /app


RUN apt-get update -y && \
    apt-get install -y python3 python3-pip tesseract-ocr libtesseract-dev libleptonica-dev pkg-config poppler-utils libgl1

COPY requirements.txt /app/requirements.txt
COPY form-tools/requirements-dev.txt /app/requirements-dev.txt
RUN pip install --break-system-packages -r requirements.txt && \
    pip install --break-system-packages -r requirements-dev.txt

ENTRYPOINT ["pytest", "tests/", "-vv"]
