ARG FUNCTION_DIR="/function"

# === BUILD IMAGE ===
FROM python:3.12-slim AS builder
# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Set the working directory to /app
WORKDIR ${FUNCTION_DIR}
# Copy the requirements file to the working directory
COPY requirements.txt requirements.txt
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


# === FINAL IMAGE ===
FROM python:3.12-slim
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
    apt-get install -y libgl1-mesa-glx libglib2.0-0 poppler-utils libtesseract-dev libleptonica-dev tesseract-ocr libzbar0 libzbar-dev && \
    rm -rf /var/lib/apt/lists/*
# Copy only the installed packages from the previous stage to the working directory
COPY --from=builder --chown=python:python ${FUNCTION_DIR} ${FUNCTION_DIR}
# Don't run as root
USER 999
# Set the entrypoint for the Lambda function
ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
# Set the command to run the Lambda handler
CMD [ "app.handler.lambda_handler" ]
