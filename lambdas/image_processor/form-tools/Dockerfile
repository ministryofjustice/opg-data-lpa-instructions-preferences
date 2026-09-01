FROM ghcr.io/astral-sh/uv@sha256:d1cbaeadc234fe19c0d93daabcf5e98738cd93c6d1dd4918ef6aa30735feb23a AS uv
FROM python:3.14.6-slim@sha256:b877e50bd90de10af8d82c57a022fc2e0dc731c5320d762a27986facfc3355c1 AS python

FROM python AS development

ENV UV_MALWARE_CHECK=1
ENV PYTHONPATH="/app"
ENV UV_LINK_MODE=copy

WORKDIR /app

# Bundle the dependencies into the Lambda task root via `uv pip install --target`.
#
# Omit any local packages (`--no-emit-workspace`)
# This ensures that the Docker layer cache is only invalidated when the `pyproject.toml` or `uv.lock`
# files change, but remains robust to changes in the application code.
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv export --frozen --no-emit-workspace --no-editable -o requirements.txt && \
    uv pip install -r requirements.txt --target "/app"

COPY form_tools tests /app/

CMD ["python", "-m", "pytest", "tests/", "-vv"]