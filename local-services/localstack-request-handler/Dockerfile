FROM localstack/localstack:1.3.1 as localstack

RUN apt -yq install bash-completion bash jq

COPY s3-uploads/LP1H-Scan.pdf /tmp/LP1H-Scan.pdf
COPY s3-uploads/LP1F-Scan.pdf /tmp/LP1F-Scan.pdf
COPY s3-uploads/LPC-Scan.pdf /tmp/LPC-Scan.pdf
COPY s3-uploads/LPC2-Scan.pdf /tmp/LPC2-Scan.pdf
COPY s3-uploads/LPA120.pdf /tmp/LPA120.pdf
COPY s3-uploads/PFA117-Scan.pdf /tmp/PFA117-Scan.pdf
COPY s3-uploads/Correspondence-Bad-Continuation-Scan.pdf /tmp/Correspondence-Bad-Continuation-Scan.pdf
COPY s3-uploads/HW114-Scan.pdf /tmp/HW114-Scan.pdf
COPY s3-uploads/LPA-PW-Scan.pdf /tmp/LPA-PW-Scan.pdf
COPY s3-uploads/PFA-C-Scan.pdf /tmp/PFA-C-Scan.pdf
COPY s3-uploads/LP1F-LP-Scan.pdf /tmp/LP1F-LP-Scan.pdf
COPY s3-uploads/LPC-LP-Scan.pdf /tmp/LPC-LP-Scan.pdf

COPY localstack-init.sh /docker-entrypoint-initaws.d/init.sh

RUN chmod 544 /docker-entrypoint-initaws.d/init.sh
