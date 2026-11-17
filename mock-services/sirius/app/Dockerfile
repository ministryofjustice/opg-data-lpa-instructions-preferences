FROM node:26.13.1-alpine3.23@sha256:39d8c143e60e99ae98f014bebea1e72fc96d3c9bdf9504bc3a27af5c05bfa39f
COPY sirius.yml run.sh /app/
RUN apk add --no-cache busybox=1.37.0-r30 ca-certificates-bundle=20261020-r0 libcrypto3=3.5.9-r0 libssl3=3.5.9-r0 ssl_client=1.37.0-r30 zlib=1.3.2-r1

WORKDIR  /app

COPY ./package.json /app/package.json
COPY ./package-lock.json /app/package-lock.json

RUN npm ci --ignore-scripts

RUN npm uninstall -g npm

RUN apk add --no-cache zlib=1.3.2-r1

RUN chown -R node:node /app

USER node

RUN chmod +x run.sh
ENTRYPOINT ["/app/run.sh"]
