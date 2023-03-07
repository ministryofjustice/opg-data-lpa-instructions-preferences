import logging
import os
import json
import shutil
import datetime
import jwt

import boto3
import requests
from botocore.exceptions import ClientError
from form_tools.form_operators import FormOperator

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ImageProcessor:
    def __init__(self, event):
        self.environment = os.getenv('ENVIRONMENT')
        self.target_environment = os.getenv('TARGET_ENVIRONMENT')
        self.secret_key_prefix = os.getenv('SECRET_PREFIX')
        self.sirius_url = os.getenv('SIRIUS_URL')
        self.sirius_url_part = os.getenv('SIRIUS_URL_PART')
        self.event = event
        self.s3 = self.setup_s3_connection()
        self.sirius_bucket = f'opg-backoffice-datastore-{self.target_environment}'
        self.iap_bucket = f'lpa-iap-{self.environment}'
        self.extraction_folder_path = 'extraction'
        self.output_folder_path = '/tmp/output'
        self.folder_name = '9999'
        self.secret_manager = self.setup_secret_manager_connection()
        self.uid = None

    def process_request(self):
        """
        Processes a request triggered from SQS and extracts instructions and preferences
        and pushes them to S3.
        Step 1: Make request to sirius endpoint when triggered by message on SQS queue
        Step 2: Use response to pull scan(s) from sirius bucket
        Step 3: Run the extraction process on the scan(s)
        Step 4: Push extracted files to the lpa-iap-env bucket
        """
        self.uid = self.get_uid_from_event()
        logger.info(f'Starting processing on {self.uid}')
        self.create_output_dir()
        s3_urls_dict = self.make_request_to_sirius(self.uid)
        logger.info(f'Response from Sirius: {str(s3_urls_dict)}')

        downloaded_scan_locations = self.download_scanned_images(s3_urls_dict)
        logger.info(f'Scan locations: {str(downloaded_scan_locations)}')

        paths_to_extracted_images = self.extract_instructions_and_preferences(downloaded_scan_locations)
        all_paths_to_extracted_images = self.add_blank_files_to_paths_with_no_match(paths_to_extracted_images)
        logger.info(f'Extracted images: {str(all_paths_to_extracted_images)}')

        self.put_images_to_bucket(all_paths_to_extracted_images)
        self.cleanup(downloaded_scan_locations)
        logger.info('Process Finished Successfully')

    @staticmethod
    def list_files(filepath, filetype):
        paths = []
        for root, dirs, files in os.walk(filepath):
            for file in files:
                if file.lower().endswith(filetype.lower()):
                    paths.append(os.path.join(root, file))
        return paths

    @staticmethod
    def get_timestamp_as_str():
        return str(int(datetime.datetime.utcnow().timestamp()))

    def create_output_dir(self):
        # define the path to the output directory
        output_dir = self.output_folder_path

        # create the output directory if it doesn't already exist
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        # create subdirectories "pass" and "fail" if they don't already exist
        pass_dir = os.path.join(output_dir, "pass")
        if not os.path.exists(pass_dir):
            os.mkdir(pass_dir)

        fail_dir = os.path.join(output_dir, "fail")
        if not os.path.exists(fail_dir):
            os.mkdir(fail_dir)

    def setup_s3_connection(self):
        if self.environment == "local":
            s3 = boto3.client("s3",
                              endpoint_url="http://localstack-request-handler:4566",
                              region_name="eu-west-1")
        else:
            s3 = boto3.client("s3", region_name="eu-west-1")
        return s3

    def setup_secret_manager_connection(self):
        if self.environment == "local":
            sm = boto3.client(
                service_name="secretsmanager",
                region_name="eu-west-1",
                endpoint_url="http://localstack-processor:4566",
                aws_access_key_id="fake",
                aws_secret_access_key="fake",  # pragma: allowlist secret
            )
        else:
            sm = boto3.client(service_name="secretsmanager", region_name="eu-west-1")
        return sm

    def cleanup(self, downloaded_image_locations):
        pass_path = f"{self.output_folder_path}/pass/{self.folder_name}"
        fail_path = f"{self.output_folder_path}/fail/{self.folder_name}"

        for path in downloaded_image_locations.values():
            if path and os.path.exists(path):
                os.remove(path)

        # Remove directories
        if os.path.exists(pass_path):
            shutil.rmtree(pass_path)
        if os.path.exists(fail_path):
            shutil.rmtree(fail_path)

    def add_blank_files_to_paths_with_no_match(self, path_to_extracted_images):
        path_to_blank_image = f'{self.extraction_folder_path}/blank.jpg'
        path_to_extracted_images_final = path_to_extracted_images
        paths_to_check = ['instructions', 'preferences', 'continuation-instructions', 'continuation-preferences']
        for path in paths_to_check:
            if path not in path_to_extracted_images:
                path_to_extracted_images_final[path] = path_to_blank_image
        return path_to_extracted_images_final

    def get_uid_from_event(self):
        message = self.event['Records'][0]['body']

        # Parse the message and get the uid value
        message_dict = json.loads(message)
        uid = message_dict['uid']
        return uid

    def make_request_to_sirius(self, uid):
        url = f"{self.sirius_url}{self.sirius_url_part}/lpas/{uid}/scans"
        headers = self.build_sirius_headers()
        logger.info(f"URL: {url}")
        try:
            response = requests.get(url=url, headers=headers)
        except requests.exceptions.RequestException as e:
            logger.error("bad response sirius")
            logger.exception(e)
            return {"error": "error getting response from Sirius"}

        logger.info(f"STATUS: {response.status_code}")
        logger.info(f"TEXT: {response.text}")

        # Parse the response and extract the values
        try:
            response_dict = json.loads(response.text)
        except json.decoder.JSONDecodeError as e:
            logger.exception(e)
            return {"error": "error decoding response from Sirius"}

        return response_dict

    @staticmethod
    def extract_s3_file_path(s3_path):
        """
        Extracts the file path from an S3 path.

        Args:
            s3_path (str): The S3 path to extract the file path from.

        Returns:
            The file path and bucket portion of the S3 path as dict.
        """
        # Remove the s3:// prefix and split the path into its components.
        path_components = s3_path[len("s3://"):].split("/", 1)
        bucket = path_components[0]

        # The first component is the bucket name, so we only need the second component.
        if len(path_components) == 2:
            file_path = path_components[1]
        else:
            file_path = ""

        return {"bucket": bucket, "file_path": file_path}

    def download_scanned_images(self, s3_urls_dict):
        lpa_scan = s3_urls_dict.get('lpaScan')
        continuation_sheet_scan = s3_urls_dict.get('continuationSheetScan', None)

        # Store the values in variables, if they exist
        lpa_location = lpa_scan.get('location') if lpa_scan else None
        continuation_locations = continuation_sheet_scan.get('location') if continuation_sheet_scan else None

        scan_locations = {}
        if lpa_location:
            path_parts = self.extract_s3_file_path(lpa_location)
            scan_location = f'{self.output_folder_path}/{path_parts["file_path"]}'
            logger.info(f"Attempting download from bucket: {path_parts['bucket']}, key: {path_parts['file_path']}, path: {scan_location}")
            self.s3.download_file(path_parts["bucket"], path_parts["file_path"], scan_location)
            scan_locations['scan'] = scan_location
        if continuation_locations and len(continuation_locations) > 0:
            location_position = 0
            for continuation_location in continuation_locations:
                location_position += 1
                path_parts = self.extract_s3_file_path(continuation_location)
                scan_location = f'{self.output_folder_path}/{path_parts["file_path"]}'
                logger.info(
                f"Attempting download from bucket: {path_parts['bucket']}, key: {path_parts['file_path']}, path: {scan_location}")
                self.s3.download_file(path_parts["bucket"], path_parts["file_path"], scan_location)
                scan_locations[f'continuation_{location_position}'] = scan_location
        return scan_locations

    def extract_instructions_and_preferences(self, image_locations):
        form_operator = FormOperator.create_from_config(f"{self.extraction_folder_path}/opg-config.yaml")

        self.folder_name = self.get_timestamp_as_str()

        for key, image_location in image_locations.items():
            _ = form_operator.run_full_pipeline(
                form_path=image_location,
                pass_dir=f"{self.output_folder_path}/pass/{self.folder_name}",
                fail_dir=f"{self.output_folder_path}/fail/{self.folder_name}",
                form_meta_directory=f"{self.extraction_folder_path}/metadata",
            )

        # Find all the file paths that we have pulled out from the scanned documents
        paths = self.list_files(f'{self.extraction_folder_path}/pass/{self.folder_name}', '.jpg')

        path_selection = {}
        for path in paths:
            if 'field_name=preferences' in path:
                path_selection['preferences'] = path
            elif 'field_name=instructions' in path:
                path_selection['instructions'] = path

        return path_selection

    def put_images_to_bucket(self, path_selection):
        for key, value in path_selection.items():
            image = f'iap-{self.uid}-{key}'
            try:
                self.s3.put_object(Bucket=self.iap_bucket, Key=image, Body=open(value, 'rb'),
                                   ServerSideEncryption='AES256')
                logger.info(f"File '{image}' added to the '{self.iap_bucket}' bucket.")
            except Exception as e:
                logger.error(f"Error: Failed to add file '{image}' to the '{self.iap_bucket}' bucket. {e}")
                raise

    def get_secret(self):
        """
        Gets and decrypts the JWT secret from AWS Secrets Manager for the chosen environment
        Args:
            environment: AWS environment name
        Returns:
            JWT secret
        Raises:
            ClientError
        """
        secret_name = f"{self.secret_key_prefix}/jwt-key"

        print(f"SECRET_NAME: {secret_name}")
        try:
            get_secret_value_response = self.secret_manager.get_secret_value(SecretId=secret_name)
            secret = get_secret_value_response["SecretString"]
        except ClientError as e:
            logger.info("Unable to get secret from Secrets Manager")
            raise e

        return secret

    def build_sirius_headers(self):
        """
        Builds headers for Sirius request, including JWT auth
        Returns:
            Header dictionary with content type and auth token
        """
        content_type = "application/json"
        session_data = os.environ["SESSION_DATA"]
        secret = self.get_secret()

        encoded_jwt = jwt.encode(
            {
                "session-data": session_data,
                "iat": datetime.datetime.utcnow(),
                "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=3600),
            },
            secret,
            algorithm="HS256",
        )

        return {
            "Content-Type": content_type,
            "Authorization": "Bearer " + encoded_jwt,
        }


def get_healthcheck_response():
    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "headers": {},
        "body": "LPA IAP Processor Lambda Health - OK"
    }


def lambda_handler(event, context):
    image_processor = ImageProcessor(event)
    image_processor.process_request()
