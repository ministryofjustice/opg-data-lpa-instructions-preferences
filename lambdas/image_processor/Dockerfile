ARG FUNCTION_DIR="/function"

# === BUILD IMAGE ===
FROM python:3.14-slim@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6 AS builder
# Include global arg in this stage of the build
ARG FUNCTION_DIR
COPY --from=ghcr.io/astral-sh/uv@sha256:b46b03ddfcfbf8f547af7e9eaefdf8a39c8cebcba7c98858d3162bd28cf536f6 /uv /uvx /bin/
# Set the working directory to /app
WORKDIR ${FUNCTION_DIR}
# Copy the lockfile and export it to a requirements file
COPY pyproject.toml uv.lock ./
RUN uv export --locked -o requirements.txt
# Install tesseract build dependencies
RUN apt-get update && \
    apt-get upgrade expat -y && \
    apt-get install -y libtesseract-dev libleptonica-dev tesseract-ocr build-essential && \
    rm -rf /var/lib/apt/lists/*
# Pip dependency installs
RUN python -m pip install --upgrade pip
RUN python -m pip install \
        --target ${FUNCTION_DIR} \
        --requirement requirements.txt
COPY app ${FUNCTION_DIR}/app
COPY extraction ${FUNCTION_DIR}/extraction
COPY form-tools/form_tools ${FUNCTION_DIR}/form_tools

# === FINAL IMAGE ===
FROM python:3.14-slim@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6
# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Create python user
RUN groupadd -g 999 python && \
    useradd -r -u 999 -g python python
# Set the working directory to /function
WORKDIR ${FUNCTION_DIR}
# Install runtime dependencies
RUN apt-get update && \
    apt-get upgrade expat -y && \
    apt-get install -y libgl1 poppler-utils libtesseract-dev libleptonica-dev tesseract-ocr tesseract-ocr-eng libzbar0 libzbar-dev && \
    rm -rf /var/lib/apt/lists/*

RUN apt remove -y libraw23t64 libopenexr-3-1-30 libopenexr-dev

# Copy only the installed packages from the previous stage to the working directory
COPY --from=builder --chown=python:python ${FUNCTION_DIR} ${FUNCTION_DIR}
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
# Don't run as root
USER 999
# Set the entrypoint for the Lambda function
ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
# Set the command to run the Lambda handler
CMD [ "app.handler.lambda_handler" ]
