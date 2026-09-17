detected_ARCH:=$(shell uname -m)
detected_OS=$(shell uname -s)
rie_sum_arm64=8159172a2dc2ce5bf434ba94d7241f2252d1ac30b58410c7e30a4b8afefd7cca
rie_sum_x86_64=3a3494331c212c14366c1073fdc4f0078f58a927da64479413879b0d84e21f20
rie_sum=$(rie_sum_$(detected_ARCH))
ifeq ($(detected_OS),Darwin)
	shacmd=shasum
else ifeq ($(detected_OS),Linux)
	shacmd=sha256sum
endif

setup:
	mkdir -p ./lambdas/.aws-lambda-rie && \
    curl -Lo ./lambdas/.aws-lambda-rie/aws-lambda-rie https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/download/v1.35/aws-lambda-rie-$(detected_ARCH)
	echo "$(rie_sum)  ./lambdas/.aws-lambda-rie/aws-lambda-rie" | $(shacmd) --check
	chmod +x ./lambdas/.aws-lambda-rie/aws-lambda-rie

up: setup
	docker compose up --build --remove-orphans -d

down:
	docker compose down

test: setup
	docker compose up unit-tests-processor

integration-test: up
	docker compose up integration-test --remove-orphans

