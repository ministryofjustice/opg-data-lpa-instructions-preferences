#!/bin/sh
set -e

awslocal secretsmanager create-secret --name "local/jwt-key" --secret-string "FAKETOKEN" --region eu-west-1

echo "Creating SQS queue"

awslocal sqs create-queue --queue-name local-lpa-iap-requests --attributes '{"MaximumMessageSize": "102400"}' --region eu-west-1 

echo "Creating image-processor lambda"

zip lambda.zip forwarder.py

awslocal lambda create-function \
          --function-name image-processor \
          --region eu-west-1 \
          --runtime python3.11 \
          --zip-file fileb://lambda.zip \
          --handler forwarder.handler \
          --timeout 600 \
          --role arn:aws:iam::000000000000:role/lambda-role

echo "Creating event source mapping"

awslocal lambda create-event-source-mapping \
         --function-name image-processor \
         --batch-size 1 \
         --event-source-arn arn:aws:sqs:eu-west-1:000000000000:local-lpa-iap-requests \
         --region eu-west-1 
