FROM node:lts-alpine3.23@sha256:595398b0081eacda8e1c4c5b97b76cd1020e4d58a8ebcb4843b9bca1e79e7436
COPY sirius.yml run.sh /app/
RUN apk upgrade libcrypto1.1 libcrypto3 libssl3 busybox ssl_client zlib

WORKDIR  /app

COPY ./package.json /app/package.json
COPY ./package-lock.json /app/package-lock.json

RUN npm ci --ignore-scripts

RUN npm uninstall -g npm

RUN apk upgrade --no-cache zlib

RUN chown -R node:node /app 

USER node

RUN chmod +x run.sh
ENTRYPOINT ["/app/run.sh"]
