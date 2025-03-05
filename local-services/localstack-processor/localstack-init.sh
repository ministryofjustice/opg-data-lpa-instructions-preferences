set -e

awslocal secretsmanager create-secret --name "local/jwt-key" --secret-string "FAKETOKEN"

echo "Creating SQS queue"

awslocal sqs create-queue --queue-name local-lpa-iap-requests --attributes '{"MaximumMessageSize": "102400"}'

echo "Creating image-processor lambda"

awslocal lambda create-function \
          --function-name function \
          --code ImageUri=image-processor:latest \
          --timeout=900 \
          --role arn:aws:iam::000000000:role/lambda-role

echo "Creating event source mapping"

awslocal lambda create-event-source-mapping \
         --function-name function \
         --batch-size 1 \
         --event-source-arn arn:aws:sqs:eu-west-1:000000000000:local-lpa-iap-requests
