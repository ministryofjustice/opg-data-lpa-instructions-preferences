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
curl -H 'Authorization: fakeauth' http://localhost:7010/v1/use-an-lpa/image-request-handler/700000000138
```

or

```commandline
curl -H 'Authorization: fakeauth' http://localhost:7010/v1/use-an-lpa/healthcheck
```
