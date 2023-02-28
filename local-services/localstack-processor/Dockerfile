FROM localstack/localstack:0.14 as localstack

RUN apt -yq install bash-completion bash jq

COPY localstack-init.sh /docker-entrypoint-initaws.d/init.sh

RUN chmod 544 /docker-entrypoint-initaws.d/init.sh
