FROM nginx:1.23.3-alpine
RUN apk upgrade curl libcurl
COPY nginx.conf /etc/nginx/conf.d/default.conf

CMD ["nginx", "-g", "daemon off;"]
