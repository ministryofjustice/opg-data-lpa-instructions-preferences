FROM stoplight/prism:4.10.3
COPY sirius.yml run.sh /app/
RUN apk upgrade libcrypto1.1 libssl1.1 busybox ssl_client zlib
WORKDIR  /app
RUN chmod +x run.sh
ENTRYPOINT ["/app/run.sh"]
