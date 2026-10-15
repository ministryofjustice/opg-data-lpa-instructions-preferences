FROM nginx:alpine3.24-slim@sha256:ebd058041a732a2b2dc0b606e34572dd8e0034de6a4aa4d50d8c13a240ac6005

RUN apk upgrade curl libcurl openssl libssl3 libcrypto3 zlib

COPY nginx.conf /etc/nginx/conf.d/default.conf

CMD ["nginx", "-g", "daemon off;"]
