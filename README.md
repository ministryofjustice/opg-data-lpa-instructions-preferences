# opg-data-lpa-instructions-preferences

The purpose of this repository is to provide integrations that allow us to take scanned documents
from our case management system, crop out the correct portions for 'instructions and preferences'
and to display them on the Use an LPA frontend website.

### Working with the openapi spec

The openapi spec defines what the API gateway will accept and what sort of responses it will expect to return.

It is advisable when editing the openapi spec to use a tool to check it works. You can copy and paste it into
https://editor.swagger.io/ and it will tell you if your spec is valid.

For a local setup to try out requests against, we have used an nginx container with rules that allow us to route
certain LPA uids to a prism container that acts as the API gateway.

To run:

```commandline
docker-compose up -d api-gateway
```

Then to get a response:

```commandline
curl -H 'Authorization: fakeauth' http://localhost:7010/v1/image-request/700000000138
```

or

```commandline
curl -H 'Authorization: fakeauth' http://localhost:7010/v1/healthcheck
```
### Making a local request

Bring up the image request lambda and localstack (localstack is dependency):

```commandline
docker-compose up -d image-request-handler
```

Allow a min for localstack to create the buckets etc and then run this curl command:

```commandline
curl -XPOST "http://localhost:9010/2015-03-31/functions/function/invocations" -d '{"requestContext": {"path": "/image-request/{uid}"}, "pathParameters": {"uid": "7000690000"}}'
```

This mimics the necessary event parameters passed to lambda by the API gateway.

### Making a request to an environment

Once you have built your environment by pushing to github and waiting for the GH actions workflow to complete,
amend and the run the script below to include your environment standardised name (so UML-1234 would be uml1234):

```commandline
aws-vault exec sirius-dev -- python3 ./scripts/post-request.py
```

Bear in mind you will need boto3 installed. You should do this in a virtual env (https://docs.python.org/3/library/venv.html)

### Run the unit tests locally

They can be run in docker to save you havign to set anything up. Simply run:

```commandline
docker-compose up -d unit-tests
```
