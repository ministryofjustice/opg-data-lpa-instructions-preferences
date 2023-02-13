import json
import logging
import os

import boto3
import botocore.exceptions

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# We shall be receiving event with the sirius uid in format of:
# 700000000047
# We will return an array of signed urls for images with following format:
# iap-700000000047-1, iap-700000000047-2, iap-700000000047-3, iap-700000000047-4

class ImageRequestHandler:
    def __init__(self, uid, bucket, sqs_queue):
        self.environment = os.getenv('ENVIRONMENT')
        self.s3 = self.setup_s3_connection()
        self.sqs = self.setup_sqs_connection()
        self.uid = uid
        self.bucket = bucket
        self.sqs_queue = sqs_queue
        self.total_images = 4
        self.images_to_check = self.images_to_check()
        self.url_expiration = 60

    def setup_sqs_connection(self):
        if self.environment == "local":
            sqs = boto3.client("sqs",
                               endpoint_url="http://localstack:4566",
                               region_name="eu-west-1")
        else:
            sqs = boto3.client("sqs", region_name="eu-west-1")
        return sqs

    def setup_s3_connection(self):
        if self.environment == "local":
            s3 = boto3.client("s3",
                              endpoint_url="http://localstack:4566",
                              region_name="eu-west-1")
        else:
            s3 = boto3.client("s3", region_name="eu-west-1")
        return s3

    def process_request(self):
        image_statuses = self.check_image_statuses(self.images_to_check)
        image_collection_status = self.get_image_collection_status(image_statuses)
        if image_collection_status == 'COLLECTION_NOT_STARTED':
            try:
                self.add_temp_images_to_bucket()
                self.add_to_sqs()
            except Exception as e:
                image_collection_status = 'COLLECTION_ERROR'
                logger.error(f'Unexpected error {e}')


        signed_urls = self.generate_signed_urls(image_statuses)

        message = self.formatted_message(signed_urls, image_collection_status)

        return message

    def images_to_check(self):
        return [
            f'iap-{self.uid}-1',
            f'iap-{self.uid}-2',
            f'iap-{self.uid}-3',
            f'iap-{self.uid}-4',
        ]

    def check_image_statuses(self, images_to_check):
        image_statuses = {}
        for image in images_to_check:
            print(f'checking image status for {image}')
            image_statuses[image] = self.image_status_in_bucket(image)

        print(f'image statuses: {image_statuses}')
        return image_statuses

    def image_status_in_bucket(self, image):
        # returns one of ['NOT_FOUND', 'IN_PROGRESS', 'EXISTS', 'ERROR']
        image_status = 'NOT_FOUND'
        try:
            file = self.s3.head_object(Bucket=self.bucket, Key=image)
            file_size = file['ContentLength']
            image_status = 'EXISTS' if file_size > 0 else 'IN_PROGRESS'
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.error(f"Error: {image} does not exist in the {self.bucket} bucket.")
            else:
                logger.error(f"Error: {e}")
                image_status = 'ERROR'
        except Exception as e:
            logger.error(f"Error: {e}")
            image_status = 'ERROR'

        return image_status

    def add_to_sqs(self):
        try:
            message = {'uid': self.uid}
            # Send the message to the queue
            response = self.sqs.send_message(QueueUrl=self.sqs_queue, MessageBody=json.dumps(message))
            logger.info(f"Message sent successfully: {response}")
        except botocore.exceptions.ClientError as e:
            logger.error(f"Error occurred while sending message: {e}")
            raise

    def add_temp_images_to_bucket(self):
        for image in self.images_to_check:
            try:
                self.s3.put_object(Bucket=self.bucket, Key=image, ServerSideEncryption='AES256')
                logger.error(f"Empty file '{image}' added to the '{self.bucket}' bucket.")
            except Exception as e:
                logger.error(f"Error: Failed to add empty file '{image}' to the '{self.bucket}' bucket. {e}")
                raise

        return True

    def generate_signed_urls(self, image_statuses):
        signed_urls = {}
        for image, status in image_statuses.items():
            url = self.s3.generate_presigned_url('get_object', Params={'Bucket': self.bucket, 'Key': image},
                                                 ExpiresIn=self.url_expiration)
            signed_urls[image] = url

        return signed_urls

    def formatted_message(self, signed_urls, collection_status):
        message = {
            'uid': self.uid,
            'status': collection_status,
            'signed_urls': signed_urls
        }
        return message

    def get_image_collection_status(self, image_statuses):
        image_not_found_count = 0
        image_found_count = 0
        image_in_progress_count = 0
        for image, status in image_statuses.items():
            if status == 'NOT_FOUND':
                image_not_found_count += 1
            elif status == 'IN_PROGRESS':
                image_in_progress_count += 1
            elif status == 'EXISTS':
                image_found_count += 1
            elif status == 'ERROR':
                logger.error(f'Unexpected error processing image: {image}')
            else:
                logger.error(f'Unexpected status encountered')

        if image_not_found_count < self.total_images and image_found_count < self.total_images \
                and (image_in_progress_count + image_found_count + image_not_found_count == self.total_images):
            return 'COLLECTION_IN_PROGRESS'
        elif image_not_found_count == 0 and image_in_progress_count == 0 and image_found_count == self.total_images:
            return 'COLLECTION_COMPLETE'
        elif image_in_progress_count == 0 and image_found_count == 0 and image_not_found_count == self.total_images:
            return 'COLLECTION_NOT_STARTED'
        else:
            return 'COLLECTION_ERROR'


def lambda_handler(event, context):
    environment = os.getenv("ENVIRONMENT")
    print(event['pathParameters'])
    s3_image_request_handler = ImageRequestHandler(
        uid=event['pathParameters']['uid'],
        bucket=f'lpa-iap-{environment}',
        sqs_queue=f'{environment}-lpa-iap-requests'
    )
    message = s3_image_request_handler.process_request()

    status_code = 500 if message['status'] == 'COLLECTION_ERROR' else 200

    response = {
        "isBase64Encoded": False,
        "statusCode": status_code,
        "headers": {},
        "body": message
    }

    return json.dumps(response)
