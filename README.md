# opg-data-lpa-instructions-preferences

The purpose of this repository is to provide integrations that allow us to take scanned documents
from our case management system, crop out the correct portions for 'instructions and preferences'
and to display them on the Use an LPA frontend website.

### Working with the OpenAPI spec

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

Bring up the image request lambda, image processing lambda and 2 instances of localstack and a mock sirius.

```commandline
docker-compose up -d image-request-handler
```

We use two versions of localstack as we are using lambda forwarding to avoid needing paid version of localstack.
The reason this is the case is that we can't seem to create local lambdas from images without localstack ecr
which is part of premium localstack. We could use zips but this wouldn't be a totally accurate reflection of our images.

Allow a min for localstack to create the buckets etc and check the logs for the url you will need to access
the local API gateway:

```commandline
docker-compose logs -f localstack-request-handler
```

When the setup completes you will see an URL echoed out. Copy it and curl the following endpoint (replacing the url as per logs):

```commandline
curl -XGET http://localhost:4566/restapis/bfb3jr5ved/v1/_user_request_/image-request/700000000009
```

#### OPTIONAL:
You can also directly curl lambdas in the form below if you like:
```commandline
curl -XPOST "http://localhost:9010/2015-03-31/functions/function/invocations" -d '{"requestContext": {"path": "/image-request/{uid}"}, "pathParameters": {"uid": "7000690000"}}'
```

What all this does is send a request to the local API gateway which is using the openapi spec to define it. From there it sends the
request on to the image-request-handler lambda. This lambda signs your urls and sends the uid as a message to a local SQS queue.
We then have the image-processing lambda listening to the SQS queue, which triggers when message arrives and uses the uid from the message
to perform a request against our mock sirius (defined by openapi spec and served by prism). We use the response from mock sirius to extract the
path of our local sirius s3 buckets file location and to pull out the files. We then process the files, extracting the instructions and preferences and
put them up to the local iap s3 bucket.

You can see when the process is finished by checking the logs for image-processor

```commandline
docker-compose logs -f image-processor
```

When finished we can rerun the curl that you ran above to the API gateway and you should see a status of collection completed.

You will be given signed urls that you can paste into your web browser
(you will have to change the localstack-request-handler bit of the url to localhost as you
will be external to docker). You should be able to download the images if you do it within 1 minute
otherwise you will get a token expired error.

### Making a request to an environment

Once you have built your environment by pushing to github and waiting for the GH actions workflow to complete,
amend and the run the script below to include your environment standardised name (so UML-1234 would be uml1234):

```commandline
aws-vault exec sirius-dev -- python3 ./scripts/post-request.py
```

Bear in mind you will need boto3 installed. You should do this in a virtual env (https://docs.python.org/3/library/venv.html)

### Run the unit tests locally

They can be run in docker to save you having to set anything up. Simply run:

```commandline
docker-compose up -d unit-tests
```

### Setting up UAT against real sirius

Sirius integration environment does not get wiped between deploys. Our development environment automatically hooks
up to it after it has completed its development tests. We have got 3 test cases that we can use to test real
world scenarios (700000158894, 700000158985, 700000159041).

We can check these work by using the script at this path `/scripts/post-request.py` and using the correct uid.

We can use this script `/script/wipe-images-s3.py` to wipe away any images in our iap bucket in dev to refresh the
environment for further manual testing. The act of removing the extracted images will effectively reset the process
and the next call will return a collection started response.
