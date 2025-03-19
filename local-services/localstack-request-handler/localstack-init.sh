#!/usr/bin/env bash
set -e

awslocal s3 mb s3://lpa-iap-local

awslocal s3 mb s3://opg-backoffice-datastore-local

for lpafile in /tmp/*.{pdf,tiff}
do
    awslocal s3 cp $lpafile s3://opg-backoffice-datastore-local/$(basename $lpafile)
done

#awslocal s3api put-bucket-policy \
#    --policy '{ "Statement": [ { "Sid": "DenyUnEncryptedObjectUploads", "Effect": "Deny", "Principal": { "AWS": "*" }, "Action": "s3:PutObject", "Resource": "arn:aws:s3:eu-west-1::lpa-iap-bucket/*", "Condition":  { "StringNotEquals": { "s3:x-amz-server-side-encryption": "AES256" } } }, { "Sid": "DenyUnEncryptedObjectUploads", "Effect": "Deny", "Principal": { "AWS": "*" }, "Action": "s3:PutObject", "Resource": "arn:aws:s3:eu-west-1::lpa-iap-bucket/*", "Condition":  { "Bool": { "aws:SecureTransport": false } } } ] }' \
#    --bucket "lpa-iap-bucket-local"

#awslocal s3api put-bucket-policy \
#    --policy '{ "Statement": [ { "Sid": "DenyUnEncryptedObjectUploads", "Effect": "Deny", "Principal": { "AWS": "*" }, "Action": "s3:PutObject", "Resource": "arn:aws:s3:eu-west-1::sirius-bucket/*", "Condition":  { "StringNotEquals": { "s3:x-amz-server-side-encryption": "AES256" } } }, { "Sid": "DenyUnEncryptedObjectUploads", "Effect": "Deny", "Principal": { "AWS": "*" }, "Action": "s3:PutObject", "Resource": "arn:aws:s3:eu-west-1::sirius-bucket/*", "Condition":  { "Bool": { "aws:SecureTransport": false } } } ] }' \
#    --bucket "sirius-bucket-local"

echo "Creating Lambda Function"

awslocal lambda create-function \
          --function-name function \
          --package-type Image \
          --code ImageUri=image-request-handler:latest \
          --region eu-west-1 \
          --role arn:aws:iam::000000000000:role/lambda-role

API_NAME=opg-data-lpa-instructions-preferences

echo "Creating API Gateway"
sed "s/\${region}/eu-west-1/g" /tmp/image-request-handler.yml > /tmp/image-request-handler-updated.yml
sed -i "s/\${account_id}/000000000000/g" /tmp/image-request-handler-updated.yml
sed -i "s/\$\${stageVariables.app_name}/function/g" /tmp/image-request-handler-updated.yml

cat /tmp/image-request-handler-updated.yml

awslocal apigateway import-rest-api --body file:///tmp/image-request-handler-updated.yml --parameters account_id=000000000000,region=eu-west-1,environment=local --region eu-west-1

API_ID=$(awslocal apigateway get-rest-apis --query "items[?name==\`${API_NAME}\`].id" --output text --region eu-west-1)

echo "API ID: ${API_ID}"
echo "Creating Deployment"

awslocal apigateway create-deployment \
    --region eu-west-1 \
    --rest-api-id ${API_ID} \
    --stage-name v1 \
    --variables account_id=000000000000,region=eu-west-1,app_name=function

echo "API Gateway URL: http://localhost:4566/restapis/${API_ID}/v1/_user_request_/"
echo "Example curl command: curl -XGET http://localhost:4566/restapis/${API_ID}/v1/_user_request_/image-request/700000000047"
