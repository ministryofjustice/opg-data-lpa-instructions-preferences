import json
import os
import re

from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

import boto3
import botocore.exceptions
from app.utility.custom_logging import custom_logger, get_event_details_for_logs

logger = custom_logger("request_handler")

patch_all()


class ImageRequestHandler:
    def __init__(self, uid, bucket, sqs_queue, event):
        self.environment = os.getenv("ENVIRONMENT")
        self.s3 = self.setup_s3_connection()
        self.sqs = self.setup_sqs_connection()
        self.uid = str(int(uid))
        self.bucket = bucket
        self.sqs_queue = sqs_queue
        self.images_to_check = self.images_to_check()
        self.total_images = len(self.images_to_check)
        self.image_to_store_metadata_against = f"iap-{self.uid}-instructions"
        self.continuation_sheet_instructions_count = 0
        self.continuation_sheet_preferences_count = 0
        self.continuation_sheet_unknown_count = 0
        self.url_expiration = 60
        self.event = event

    def setup_sqs_connection(self):
        if self.environment == "local":
            sqs = boto3.client(
                "sqs",
                endpoint_url="http://localstack-processor:4566",
                region_name="eu-west-1",
            )
        else:
            sqs = boto3.client("sqs", region_name="eu-west-1")
        return sqs

    def setup_s3_connection(self):
        if self.environment == "local":
            s3 = boto3.client(
                "s3",
                endpoint_url="http://localstack-request-handler:4566",
                region_name="eu-west-1",
            )
        else:
            s3 = boto3.client("s3", region_name="eu-west-1")
        return s3

    def process_request(self) -> dict:
        """
        Processes the image request and returns an HTTP response with signed URLs for processed images.

        Returns:
        - dict: HTTP response with signed URLs for processed images.
        """
        try:
            # Check the statuses of the images to be processed
            image_statuses = self.check_image_statuses(self.images_to_check)

            # Get the overall status of the image collection based on individual image statuses
            image_collection_status = self.get_image_collection_status(image_statuses)

            if image_collection_status == "COLLECTION_ERROR":
                raise Exception("Collection Error")

            # If image collection has not yet started, try to add temporary images to the bucket and add messages to SQS
            if image_collection_status == "COLLECTION_NOT_STARTED":
                self.add_temp_images_to_bucket()
                self.add_to_sqs()

            # Generate signed URLs for images that were successfully processed and format a response message
            signed_urls = self.generate_signed_urls(
                image_statuses, image_collection_status
            )
            message = self.formatted_message(signed_urls, image_collection_status)

            status_code = 200
            # This is the only place info message is logged
            logger.info(
                message["status"],
                extra=get_event_details_for_logs(self.event, status=status_code),
            )

            response = {
                "isBase64Encoded": False,
                "statusCode": status_code,
                "body": json.dumps(message),
            }
        except Exception as e:
            status_code = 200
            logger.error(
                e, extra=get_event_details_for_logs(self.event, status=status_code)
            )
            message = self.formatted_message({}, "COLLECTION_ERROR")
            response = {
                "isBase64Encoded": False,
                "statusCode": status_code,
                "body": json.dumps(message),
            }

        return response

    def images_to_check(self):
        return [f"iap-{self.uid}-instructions", f"iap-{self.uid}-preferences"]

    def check_image_statuses(self, images_to_check) -> dict:
        """
        Checks the status of images in a given list and returns a dictionary mapping each image to its status.

        Args:
        - images_to_check (list): A list of image names to check the status of.

        Returns:
        - dict: A dictionary mapping each image name to its status.
        """

        image_statuses = {}
        # Check the status of each image in the list
        for image in images_to_check:
            logger.debug(f"Checking image status for {image}")
            image_statuses[image] = self.image_status_in_bucket(image)

        # Check the status of continuation instruction images
        for index in range(self.continuation_sheet_instructions_count):
            continuation_instruction_image = (
                f"iap-{self.uid}-continuation_instructions_{index + 1}"
            )
            try:
                logger.debug(
                    f"Checking continuation instruction image status for: {continuation_instruction_image}"
                )
                image_statuses[
                    continuation_instruction_image
                ] = self.image_status_in_bucket(continuation_instruction_image)
            except Exception as e:
                raise Exception(
                    f"Error assigning image status for instruction "
                    f"continuation sheets {continuation_instruction_image}: {e}"
                )

        # Check the status of continuation preference images
        for index in range(self.continuation_sheet_preferences_count):
            continuation_preference_image = (
                f"iap-{self.uid}-continuation_preferences_{index + 1}"
            )
            try:
                logger.debug(
                    f"Checking continuation preference image status for: {continuation_preference_image}"
                )
                image_statuses[
                    continuation_preference_image
                ] = self.image_status_in_bucket(continuation_preference_image)
            except Exception as e:
                raise Exception(
                    f"Error assigning image status for preference  "
                    f"continuation sheets {continuation_preference_image}: {e}"
                )

        # Check the status of continuation preference images
        for index in range(self.continuation_sheet_unknown_count):
            continuation_unknown_image = (
                f"iap-{self.uid}-continuation_unknown_{index + 1}"
            )
            try:
                logger.debug(
                    f"Checking continuation preference image status for: {continuation_unknown_image}"
                )
                image_statuses[
                    continuation_unknown_image
                ] = self.image_status_in_bucket(continuation_unknown_image)
            except Exception as e:
                raise Exception(
                    f"Error assigning image status for unknown  "
                    f"continuation sheets {continuation_unknown_image}: {e}"
                )

        logger.debug(f"Image statuses: {image_statuses}")
        return image_statuses

    def image_status_in_bucket(self, image: str) -> str:
        """
        Returns the status of an image in a bucket. The status is one of
        ['NOT_FOUND', 'IN_PROGRESS', 'EXISTS'].

        Args:
        - image (str): The name of the image to check the status of.

        Returns:
        - str: The status of the image in the bucket.
        """

        image_status = "NOT_FOUND"

        try:
            file = self.s3.head_object(Bucket=self.bucket, Key=image)
            file_size = file["ContentLength"]
            if image == self.image_to_store_metadata_against:
                self.continuation_sheet_instructions_count = int(
                    file["Metadata"]["continuationsheetsinstructions"]
                )
                self.continuation_sheet_preferences_count = int(
                    file["Metadata"]["continuationsheetspreferences"]
                )
                self.continuation_sheet_unknown_count = int(
                    file["Metadata"]["continuationsheetsunknown"]
                )
                process_error = file["Metadata"]["processerror"]
                if process_error == "1":
                    return "ERROR"
            image_status = "EXISTS" if file_size > 0 else "IN_PROGRESS"
        except botocore.exceptions.ClientError as e:
            logger.debug(f"Error code: {e.response['Error']['Code']}")
            if e.response["Error"]["Code"] == "404":
                logger.debug(f"{image} does not yet exist in the {self.bucket} bucket.")
            else:
                raise Exception(f"Client Error: {e}")
        except Exception as e:
            raise Exception(e)

        return image_status

    def add_to_sqs(self) -> None:
        """
        Adds a message to an SQS queue.
        """
        try:
            message = {"uid": self.uid}
            response = self.sqs.send_message(
                QueueUrl=self.sqs_queue, MessageBody=json.dumps(message)
            )
            logger.debug(f"Message sent successfully: {response}")
        except botocore.exceptions.ClientError as e:
            raise Exception(f"Error occurred while sending message to SQS: {e}")

    def add_temp_images_to_bucket(self) -> bool:
        """
        Add temporary images to the bucket

        Returns: bool
        """
        for image in self.images_to_check:
            try:
                self.s3.put_object(
                    Bucket=self.bucket,
                    Key=image,
                    ServerSideEncryption="AES256",
                    Metadata={
                        "ContinuationSheetsInstructions": "0",
                        "ContinuationSheetsPreferences": "0",
                        "ContinuationSheetsUnknown": "0",
                        "ProcessError": "0",
                    },
                )
                logger.debug(
                    f"Empty file '{image}' added to the '{self.bucket}' bucket."
                )
            except Exception as e:
                raise Exception(
                    f"Error: Failed to add empty file '{image}' to the '{self.bucket}' bucket. {e}"
                )

        return True

    def generate_signed_urls(self, image_statuses, image_collection_status) -> dict:
        """
        Generate signed URLs for images that exist in the S3 bucket and have been collected successfully.
        :param image_statuses: A dictionary containing the statuses of the images that have been checked
        :param image_collection_status: A string representing the overall status of the image collection process
        :return: A dictionary containing signed URLs for successful images that exist in the S3 bucket
        """
        signed_urls = {}
        if image_collection_status == "COLLECTION_COMPLETE":
            for image, _ in image_statuses.items():
                try:
                    url = self.s3.generate_presigned_url(
                        "get_object",
                        Params={"Bucket": self.bucket, "Key": image},
                        ExpiresIn=self.url_expiration,
                    )
                except Exception as e:
                    raise Exception(f"Error generating pre-signed url: {e}")
                signed_urls[image] = url

        return signed_urls

    def formatted_message(self, signed_urls, collection_status):
        """
        formats the message to be ingested by UAL
        """
        message = {
            "uId": int(self.uid),
            "status": collection_status,
            "signedUrls": signed_urls,
        }
        return message

    def get_image_collection_status(self, image_statuses) -> str:
        """
        Determines the status of the image collection based on the statuses of its individual images.

        Args:
            image_statuses (Dict[str, str]): A dictionary containing the statuses of individual images:
                'NOT_FOUND': The image does not exist in the S3 bucket.
                'IN_PROGRESS': The image is still being processed.
                'EXISTS': The image exists in the S3 bucket and has been processed.
                'ERROR': There was an error processing the image.

        Returns:
            str: The status of the image collection. The status can be one of the following:
                'COLLECTION_IN_PROGRESS': At least one image is in progress
                'COLLECTION_COMPLETE': All images have been processed successfully.
                'COLLECTION_NOT_STARTED': None of the images have been processed yet.
                'COLLECTION_ERROR': There was an error processing at least one of the images.
        """
        status_counts = {"NOT_FOUND": 0, "IN_PROGRESS": 0, "EXISTS": 0, "ERROR": 0}
        self.total_images = len(image_statuses)
        for status in image_statuses.values():
            if status in status_counts:
                status_counts[status] += 1
            else:
                raise Exception("Unexpected status encountered in collection")

        if status_counts["ERROR"] > 0:
            return "COLLECTION_ERROR"
        elif status_counts["IN_PROGRESS"] > 0:
            return "COLLECTION_IN_PROGRESS"
        elif status_counts["NOT_FOUND"] == self.total_images:
            return "COLLECTION_NOT_STARTED"
        else:
            return "COLLECTION_COMPLETE"


def get_healthcheck_response(event):
    logger.info("OK", extra=get_event_details_for_logs(event, status=200))
    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "body": "LPA IAP Request Handler Lambda Health - OK",
    }


def sanitize_path_parameter(value):
    if value is None:
        return None
    # Keep only numeric characters to avoid injection
    return re.sub(r"[^0-9]", "", value)


@xray_recorder.capture()
def lambda_handler(event, context):
    environment = os.getenv("ENVIRONMENT")
    version = os.getenv("VERSION")

    # Check what the path is and call different functions accordingly
    if event["requestContext"]["resourcePath"] in [
        "/healthcheck",
        "/" + version + "/healthcheck",
    ]:
        response = get_healthcheck_response(event)
    elif event["requestContext"]["resourcePath"] in [
        "/image-request/{uid}",
        "/" + version + "/image-request/{uid}",
    ]:
        uid = sanitize_path_parameter(event["pathParameters"].get("uid"))

        current_segment = xray_recorder.current_segment()
        current_segment.put_annotation("uid", uid)

        s3_image_request_handler = ImageRequestHandler(
            uid=uid,
            bucket=f"lpa-iap-{environment}",
            sqs_queue=f"{environment}-lpa-iap-requests",
            event=event,
        )
        response = s3_image_request_handler.process_request()
        xray_recorder.end_subsegment()
    else:
        response = {
            "isBase64Encoded": False,
            "statusCode": 404,
            "body": f"Not Found - Non existent path ({event['requestContext']['resourcePath']}) requested",
        }

    return response
