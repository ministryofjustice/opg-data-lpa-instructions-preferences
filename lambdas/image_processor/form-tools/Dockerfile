FROM ghcr.io/astral-sh/uv@sha256:10787c682e4184e4f290de1171fd4703dc63de99221f10fe1c99002ce7fa9acc AS uv
FROM python:3.14.6-slim@sha256:7bec7ddcddeff7975d6ba9b4be7dd6f6b2f55e7491539145e2978f7f97ce9144 AS python

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