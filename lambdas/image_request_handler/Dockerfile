# Define function directory
ARG FUNCTION_DIR="/function"
FROM python:3.13-alpine3.21 AS python-alpine
RUN apk add libstdc++

RUN apk upgrade libcrypto1.1 libcom_err ncurses-terminfo-base ncurses-libs libssl3 libcrypto3

RUN pip install setuptools --upgrade

# Build image
FROM python-alpine as build-image
# Install aws-lambda-cpp build dependencies
RUN apk add  --no-cache \
    build-base \
    libtool \
    autoconf \
    automake \
    elfutils-dev \
    make \
    cmake \
    libcurl

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Create function directory
RUN mkdir -p ${FUNCTION_DIR}
# Copy function code
COPY app ${FUNCTION_DIR}/app
COPY requirements.txt requirements.txt
# Install the runtime interface client
RUN python -m pip install --upgrade pip
RUN python -m pip install \
        --target ${FUNCTION_DIR} \
        --requirement requirements.txt


# Multi-stage build: grab a fresh copy of the base image
FROM python-alpine

# Add libzstd  library - needed for awslambdaric's runtime_client module
RUN apk add zstd-libs
# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}
# Copy in the build image dependencies
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
CMD [ "app.handler.lambda_handler" ]
