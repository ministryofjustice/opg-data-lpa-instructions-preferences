FROM localstack/localstack:4.1.0 as localstack

RUN apt -yq install bash-completion bash jq

COPY localstack-init.sh /docker-entrypoint-initaws.d/init.sh

RUN chmod 544 /docker-entrypoint-initaws.d/init.sh
