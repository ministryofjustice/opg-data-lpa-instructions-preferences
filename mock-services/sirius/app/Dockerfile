FROM stoplight/prism:5.8.0
COPY sirius.yml run.sh /app/
RUN apk upgrade libcrypto1.1 libssl1.1 busybox ssl_client zlib
RUN npm -g install npm@8.19.4
WORKDIR  /app
RUN chmod +x run.sh
ENTRYPOINT ["/app/run.sh"]
