#!/usr/bin/env bash
set -e

awslocal s3 mb s3://lpa-iap-local

awslocal s3 mb s3://opg-backoffice-datastore-local

for lpafile in /tmp/*.{pdf,tiff}
do
    awslocal s3 cp $lpafile s3://opg-backoffice-datastore-local/$(basename $lpafile)
done

echo "Creating Lambda Function"

zip lambda.zip forwarder.py

awslocal lambda create-function \
          --function-name image-request-handler \
          --region eu-west-1 \
          --runtime python3.11 \
          --zip-file fileb://lambda.zip \
          --handler forwarder.handler \
          --role arn:aws:iam::000000000000:role/lambda-role

API_NAME=opg-data-lpa-instructions-preferences

echo "Creating API Gateway"
sed "s/\${region}/eu-west-1/g" /tmp/image-request-handler.yml > /tmp/image-request-handler-updated.yml
sed -i "s/\${account_id}/000000000000/g" /tmp/image-request-handler-updated.yml
sed -i "s/\$\${stageVariables.app_name}/image-request-handler/g" /tmp/image-request-handler-updated.yml

cat /tmp/image-request-handler-updated.yml

awslocal apigateway import-rest-api --body file:///tmp/image-request-handler-updated.yml --parameters account_id=000000000000,region=eu-west-1,environment=local --region eu-west-1

API_ID=$(awslocal apigateway get-rest-apis --query "items[?name==\`${API_NAME}\`].id" --output text --region eu-west-1)

echo "API ID: ${API_ID}"
echo "Creating Deployment"

awslocal apigateway create-deployment \
    --region eu-west-1 \
    --rest-api-id ${API_ID} \
    --stage-name v1 \
    --variables account_id=000000000000,region=eu-west-1,app_name=image-request-handler

echo "API Gateway URL: http://localhost:4566/restapis/${API_ID}/v1/_user_request_/"
echo "Example curl command: curl -XGET http://localhost:4566/restapis/${API_ID}/v1/_user_request_/image-request/700000000047"
