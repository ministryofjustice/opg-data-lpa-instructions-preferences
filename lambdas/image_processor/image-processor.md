### Image processor

This receives messages from a queue that tells it which document to pull from a s3 bucket.
It then performs the extraction of the instructions and preferences on the document and sends
the resulting images to a location that our application can make use of.
