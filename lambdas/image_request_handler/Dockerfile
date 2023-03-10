# Define function directory
ARG FUNCTION_DIR="/function"
FROM python:3.10.9-alpine3.16 AS python-alpine
RUN apk add libstdc++
# Upgrade insecure packages (can't use alpine 3.17 as no libexecinfo-dev)
RUN apk upgrade libcrypto1.1 libssl1.1 libcom_err
RUN pip install setuptools --upgrade

# Build image
FROM python-alpine as build-image
# Install aws-lambda-cpp build dependencies
RUN apk add  --no-cache \
    build-base \
    libtool \
    autoconf \
    automake \
    libexecinfo-dev \
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
# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}
# Copy in the build image dependencies
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
CMD [ "app.handler.lambda_handler" ]
