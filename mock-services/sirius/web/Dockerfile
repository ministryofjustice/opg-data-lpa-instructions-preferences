FROM nginx:alpine3.23-slim
RUN apk upgrade curl libcurl openssl libssl3 libcrypto3 zlib

COPY nginx.conf /etc/nginx/conf.d/default.conf

CMD ["nginx", "-g", "daemon off;"]
