### Image request handler

This lambda handles requests for signed images from the use an LPA application. Where the image 
doesn't exist it adds a temporary image to our bucket and sends a message to a queue to be picked up by the 
image processor lambda.