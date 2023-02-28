FROM localstack/localstack:latest as localstack

RUN apt -yq install bash-completion bash jq

COPY s3-uploads/LP1H-Scan.pdf /tmp/LP1H-Scan.pdf
COPY s3-uploads/LPC-Scan.pdf /tmp/LPC-Scan.pdf
COPY localstack-init.sh /docker-entrypoint-initaws.d/init.sh

RUN chmod 544 /docker-entrypoint-initaws.d/init.sh
