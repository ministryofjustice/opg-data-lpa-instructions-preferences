FROM nginx:alpine3.24-slim@sha256:c293b28729906d97fa5302fce3bd79bd27a3ea9a5d9604e21c6ff0ebf14549fc

RUN apk add --no-cache ca-certificates-bundle=20261020-r0 libcrypto3=3.5.9-r1 libssl3=3.5.9-r1 zlib=1.3.2-r1

COPY nginx.conf /etc/nginx/conf.d/default.conf

CMD ["nginx", "-g", "daemon off;"]
