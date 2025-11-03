FROM localstack/localstack:4.10.0 as localstack

RUN apt -yq install bash-completion bash jq

COPY s3-uploads/ /tmp

COPY localstack-init.sh /etc/localstack/init/ready.d/localstack-init.sh

COPY forwarder.py forwarder.py

RUN chmod 544 /etc/localstack/init/ready.d/localstack-init.sh
