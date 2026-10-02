FROM nginx:alpine3.24-slim@sha256:f761b94f2cb9e8e05e2943d5f773609596113ef69b54e2433a996d109a8f78b7

RUN apk upgrade curl libcurl openssl libssl3 libcrypto3 zlib

COPY nginx.conf /etc/nginx/conf.d/default.conf

CMD ["nginx", "-g", "daemon off;"]
