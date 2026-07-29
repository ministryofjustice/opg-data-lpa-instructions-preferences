FROM python:3.14-alpine3.23@sha256:b165067c5afc37fa5608a3c05609cc3d51aafd808a30fbfd822ee594fef55ad4

COPY --from=ghcr.io/astral-sh/uv@sha256:b46b03ddfcfbf8f547af7e9eaefdf8a39c8cebcba7c98858d3162bd28cf536f6 /uv /uvx /bin/

RUN mkdir /app
WORKDIR /app

COPY config.py config.py
COPY test_end_to_end.py test_end_to_end.py
COPY pyproject.toml uv.lock ./
RUN uv export --locked -o requirements.txt \
    && pip install --no-cache-dir -r requirements.txt \
    && rm requirements.txt

ENTRYPOINT ["python", "-m", "pytest", "."]
