FROM node:lts-alpine3.23@sha256:7fddd9ddeae8196abf4a3ef2de34e11f7b1a722119f91f28ddf1e99dcafdf114
COPY sirius.yml run.sh /app/
RUN apk upgrade libcrypto1.1 libcrypto3 libssl3 busybox ssl_client zlib

WORKDIR  /app

RUN  npm install @stoplight/prism-cli

RUN npm update tar lodash fast-xml-parser --save

RUN npm uninstall -g npm



RUN chmod +x run.sh
ENTRYPOINT ["/app/run.sh"]
