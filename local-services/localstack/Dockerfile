FROM localstack/localstack:1.3.1 as localstack

RUN apt -yq install bash-completion bash jq

COPY ./s3-uploads/good.png /tmp/good.png
COPY ./localstack-init.sh /docker-entrypoint-initaws.d/init.sh

RUN chmod 544 /docker-entrypoint-initaws.d/init.sh
