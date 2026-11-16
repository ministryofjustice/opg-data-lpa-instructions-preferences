FROM nginx:alpine3.24-slim@sha256:4c734d33ee731135dc9f2349914a34551c920f4451fca8bb05bf5880eb9079e8

RUN apk add --no-cache ca-certificates-bundle=20261020-r0 libcrypto3=3.5.9-r0 libssl3=3.5.9-r0 zlib=1.3.2-r1

COPY nginx.conf /etc/nginx/conf.d/default.conf

CMD ["nginx", "-g", "daemon off;"]
