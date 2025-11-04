FROM stoplight/prism:5.14.3
COPY sirius.yml run.sh /app/
RUN apk upgrade libcrypto1.1 libssl3 busybox ssl_client zlib

RUN rm -rf /usr/local/lib/node_modules/npm/node_modules/cross-spawn
RUN npm install cross-spawn@7.0.5 --prefix /usr/local/lib/node_modules/npm/node_modules --no-save

WORKDIR  /app
RUN chmod +x run.sh
ENTRYPOINT ["/app/run.sh"]
