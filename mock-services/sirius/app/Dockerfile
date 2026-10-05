FROM node:lts-alpine3.23@sha256:9ec4a2e289874ed0d722e1772ec2de45d2801541db8612f3638b26f128c69ac2
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
