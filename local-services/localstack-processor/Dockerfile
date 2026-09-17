FROM localstack/localstack:4.14.0 AS localstack

RUN apt update && \
    DEBIAN_FRONTEND=noninteractive apt -yq install --only-upgrade perl perl-base perl-modules-5.40 && \
    apt -yq install bash-completion bash jq

COPY localstack-init.sh /etc/localstack/init/ready.d/localstack-init.sh

COPY forwarder.py forwarder.py

RUN chmod 544 /etc/localstack/init/ready.d/localstack-init.sh
