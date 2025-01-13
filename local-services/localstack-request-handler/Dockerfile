FROM localstack/localstack:4.0.3 as localstack

RUN apt -yq install bash-completion bash jq

COPY s3-uploads/ /tmp

COPY localstack-init.sh /docker-entrypoint-initaws.d/init.sh

RUN chmod 544 /docker-entrypoint-initaws.d/init.sh
