FROM stoplight/prism:4.10.6
COPY sirius.yml run.sh /app/
RUN apk upgrade libcrypto1.1 libssl1.1 busybox ssl_client zlib
RUN npm -g install npm@latest
WORKDIR  /app
RUN chmod +x run.sh
ENTRYPOINT ["/app/run.sh"]
