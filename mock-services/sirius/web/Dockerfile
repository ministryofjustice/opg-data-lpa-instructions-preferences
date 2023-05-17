FROM nginx:alpine3.17-slim
RUN apk upgrade curl libcurl
COPY nginx.conf /etc/nginx/conf.d/default.conf

CMD ["nginx", "-g", "daemon off;"]
