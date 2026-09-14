ARG FUNCTION_DIR="/function"

FROM ghcr.io/astral-sh/uv@sha256:b485bd65cc2cf1c9a93b3554012c9c3778cf7b1b5fd3d3096ce9e1226c97e1e6 AS uv
FROM python:3.14.6-slim@sha256:b877e50bd90de10af8d82c57a022fc2e0dc731c5320d762a27986facfc3355c1 AS python

FROM python AS builder

ARG FUNCTION_DIR
ENV UV_MALWARE_CHECK=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_INSTALLER_METADATA=1
ENV UV_LINK_MODE=copy

WORKDIR ${FUNCTION_DIR}

# Install tesseract build dependencies
RUN apt-get update && \
    apt-get install -y libtesseract-dev libleptonica-dev build-essential && \
    rm -rf /var/lib/apt/lists/*

# Bundle the dependencies into the Lambda task root via `uv pip install --target`.
#
# Omit any local packages (`--no-emit-workspace`) and development dependencies (`--no-dev`).
# This ensures that the Docker layer cache is only invalidated when the `pyproject.toml` or `uv.lock`
# files change, but remains robust to changes in the application code.
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv export --frozen --no-emit-workspace --no-dev --no-editable -o requirements.txt && \
    uv pip install -r requirements.txt --target "${FUNCTION_DIR}"


FROM python AS base

ARG FUNCTION_DIR
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
ENV PYTHONPATH="/${FUNCTION_DIR}"

WORKDIR ${FUNCTION_DIR}

RUN groupadd -g 999 python && \
    useradd -r -u 999 -g python python

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-eng \
        libzbar0 \
    && rm -rf /var/lib/apt/lists/*

# Copy the runtime dependencies from the builder stage.
COPY --from=builder --chown=python:python ${FUNCTION_DIR}/ .

# Copy the application code.
COPY app ${FUNCTION_DIR}/app
COPY extraction ${FUNCTION_DIR}/extraction
COPY form-tools/form_tools ${FUNCTION_DIR}/form_tools


FROM base AS development

ARG FUNCTION_DIR
ENV UV_MALWARE_CHECK=1
ENV UV_LINK_MODE=copy

# Install development dependencies (pytest, coverage etc)
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv export --frozen --no-editable --only-dev -o requirements.txt && \
    uv pip install -r requirements.txt --target "${FUNCTION_DIR}"

COPY tests ${FUNCTION_DIR}/tests
COPY --chmod=755 run-tests.sh run-tests.sh


# Production as default target
FROM base AS production

USER python

ENTRYPOINT [ "python", "-m", "awslambdaric" ]
CMD [ "app.handler.lambda_handler" ]