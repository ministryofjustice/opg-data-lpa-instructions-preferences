FROM node:26.13.0-alpine3.23@sha256:44a3247313f9bc069a4ec25d01b66254ed7dc4d0408727d8720dc827f0753423
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
