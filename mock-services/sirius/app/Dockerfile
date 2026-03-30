FROM node:lts-alpine3.23@sha256:01743339035a5c3c11a373cd7c83aeab6ed1457b55da6a69e014a95ac4e4700b
COPY sirius.yml run.sh /app/
RUN apk upgrade libcrypto1.1 libcrypto3 libssl3 busybox ssl_client zlib

WORKDIR  /app

COPY ./package.json /app/package.json
COPY ./package-lock.json /app/package-lock.json

RUN npm ci --ignore-scripts


RUN npm update tar lodash fast-xml-parser --save

RUN npm uninstall -g npm

RUN apk upgrade --no-cache zlib

RUN chown -R node:node /app 

USER node

RUN chmod +x run.sh
ENTRYPOINT ["/app/run.sh"]
