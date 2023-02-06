import boto3

# Create an SQS client
sqs = boto3.client('sqs', endpoint_url='http://localhost:4566', region_name='eu-west-1')

# Get the URL for the queue
queue_url = sqs.get_queue_url(QueueName='lpa-image-request')['QueueUrl']

# Receive messages from the queue
response = sqs.receive_message(
    QueueUrl=queue_url,
    MaxNumberOfMessages=1
)

# Print the received messages
messages = response.get('Messages')
if messages:
    for message in messages:
        print(message['Body'])
else:
    print("No messages in the queue")
