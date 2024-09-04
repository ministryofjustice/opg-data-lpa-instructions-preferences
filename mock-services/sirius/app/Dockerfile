FROM stoplight/prism:5.11.1
COPY sirius.yml run.sh /app/
RUN apk upgrade libcrypto1.1 libssl3 busybox ssl_client zlib
RUN npm -g install npm@8.19.4
WORKDIR  /app
RUN chmod +x run.sh
ENTRYPOINT ["/app/run.sh"]
