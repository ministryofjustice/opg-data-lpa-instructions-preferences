FROM python:3.14-slim@sha256:b877e50bd90de10af8d82c57a022fc2e0dc731c5320d762a27986facfc3355c1

COPY --from=ghcr.io/astral-sh/uv@sha256:b46b03ddfcfbf8f547af7e9eaefdf8a39c8cebcba7c98858d3162bd28cf536f6 /uv /uvx /bin/

RUN mkdir /app
WORKDIR /app

RUN apt-get update -y && \
    apt-get install -y tesseract-ocr libtesseract-dev libleptonica-dev pkg-config poppler-utils libgl1 && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock /app/
RUN uv export --locked -o requirements.txt

COPY form-tools/pyproject.toml form-tools/uv.lock /app/form-tools/
RUN uv export --directory form-tools --locked -o requirements-dev.txt

RUN pip install -r requirements.txt && \
    pip install -r form-tools/requirements-dev.txt

ENTRYPOINT ["pytest", "tests/", "-vv"]
