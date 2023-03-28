import logging
import os
import json
import shutil
import datetime
import time

import jwt
import cv2
import numpy as np

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
        self.continuation_instruction_count = 0
        self.continuation_preference_count = 0
        self.secret_manager = self.setup_secret_manager_connection()
        self.uid = None

    def process_request(self):
        """
        Main Process that receives a request triggered from SQS and extracts the
        instructions and preferences and pushes them to S3.
        """
        self.uid = self.get_uid_from_event()
        logger.info(f'Starting processing on {self.uid}')
        self.create_output_dir()

        # Get response from sirius for all scanned documents in s3 bucket for given UID
        sirius_response_dict = self.make_request_to_sirius(self.uid)
        logger.info(f'Response from Sirius: {str(sirius_response_dict)}')

        # Download all files from sirius and store their path locations
        downloaded_scan_locations = self.download_scanned_images(sirius_response_dict)
        logger.info(f'Scan locations: {str(downloaded_scan_locations)}')

        # Extract all relevant images relating to instructions and preferences from downloaded documents
        paths_to_extracted_images = self.extract_instructions_and_preferences(downloaded_scan_locations)
        logger.info(f"Paths to extracted images: {paths_to_extracted_images}")

        # Update the counts that will be pushed as metadata
        self.update_continuation_sheet_counts(paths_to_extracted_images)

        # Push images up to the buckets
        self.put_images_to_bucket(paths_to_extracted_images)

        # Cleanup all the folders
        self.cleanup(downloaded_scan_locations)
        logger.info('Process Finished Successfully')

    @staticmethod
    def list_files(filepath: str, filetype: str) -> list:
        """
        Returns a list of file paths that match the specified file type in the specified directory and its subdirectories.

        Args:
        - filepath (str): The path to the directory to search for files.
        - filetype (str): The file type to look for, e.g. ".txt", ".pdf", etc.

        Returns:
        - A list of file paths (str) that match the specified file type.
        """
        paths = []
        for root, dirs, files in os.walk(filepath):
            for file in files:
                if file.lower().endswith(filetype.lower()):
                    paths.append(os.path.join(root, file))
        return paths

    @staticmethod
    def get_timestamp_as_str():
        return str(int(datetime.datetime.utcnow().timestamp()))

    def create_output_dir(self) -> None:
        """
        Creates the output directory and two subdirectories ("pass" and "fail") if they don't already exist.
        """
        # Define the path to the output directory
        output_dir = self.output_folder_path

        # Create the output directory if it doesn't already exist
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        # Create subdirectories "pass" and "fail" if they don't already exist
        pass_dir = os.path.join(output_dir, "pass")
        if not os.path.exists(pass_dir):
            os.mkdir(pass_dir)

        fail_dir = os.path.join(output_dir, "fail")
        if not os.path.exists(fail_dir):
            os.mkdir(fail_dir)

    def setup_s3_connection(self) -> boto3.client:
        """
        Sets up an S3 connection object based on the environment specified by the instance variable "environment".
        If the environment is "local", the connection object will use the local endpoint URL for testing purposes.

        Returns:
        - An S3 connection object (boto3.client).
        """
        if self.environment == "local":
            s3 = boto3.client("s3",
                              endpoint_url="http://localstack-request-handler:4566",
                              region_name="eu-west-1")
        else:
            s3 = boto3.client("s3", region_name="eu-west-1")
        return s3

    def setup_secret_manager_connection(self) -> boto3.client:
        """
        Sets up a connection to AWS Secrets Manager based on the environment specified by the instance variable "environment".
        If the environment is "local", the connection object will use the local endpoint URL for testing purposes.

        Returns:
        - A connection to AWS Secrets Manager (boto3.client).
        """
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
        """
        Cleans up downloaded images and removes the pass and fail directories created during the image processing.
        Also removes any pdfs older than one hour and any pass and fail folders older than 1 hour.

        Args:
        - downloaded_image_locations (dict): A dictionary containing the paths to the downloaded images.
        """
        # Remove downloaded images
        for path in downloaded_image_locations.values():
            if path and os.path.exists(path):
                os.remove(path)

        # Remove pass and fail directories
        pass_path = f"{self.output_folder_path}/pass"
        fail_path = f"{self.output_folder_path}/fail"

        one_hour_ago = time.time() - 3600

        for file_name in os.listdir(self.output_folder_path):
            file_path = os.path.join(self.output_folder_path, file_name)
            if os.path.isfile(file_path) and file_name.endswith('.pdf'):
                file_modified_time = os.path.getmtime(file_path)
                if file_modified_time < one_hour_ago:
                    os.remove(file_path)

        for folder_path in [pass_path, fail_path]:
            for subfolder_name in os.listdir(folder_path):
                subfolder_path = os.path.join(folder_path, subfolder_name)
                if os.path.isdir(subfolder_path):
                    try:
                        timestamp = int(subfolder_name)
                        if timestamp < one_hour_ago:
                            shutil.rmtree(subfolder_path)
                    except ValueError:
                        pass
                    if subfolder_name == self.folder_name:
                        if os.path.exists(subfolder_path):
                            shutil.rmtree(subfolder_path)

    def get_uid_from_event(self):
        message = self.event['Records'][0]['body']

        # Parse the message and get the uid value
        message_dict = json.loads(message)
        uid = message_dict['uid']
        return uid

    def make_request_to_sirius(self, uid):
        """
        Sends a GET request to the Sirius API to retrieve scans associated with a given UID.

        Args:
        - uid (str): A unique identifier for a particular record.

        Returns:
        - response_dict (dict): A dictionary containing the response from Sirius.
          If an error occurred, the dictionary will contain an "error" key with an error message as the value.
        """
        url = f"{self.sirius_url}{self.sirius_url_part}/lpas/{uid}/scans"
        headers = self.build_sirius_headers()
        logger.info(f"Sending request to Sirius on url: {url}")

        try:
            response = requests.get(url=url, headers=headers)
        except requests.exceptions.RequestException as e:
            logger.error("Bad response from Sirius")
            logger.exception(e)
            return {"error": "Error getting response from Sirius"}

        logger.info(f"Response from Sirius: {response.text}, Status: {response.status_code}")

        try:
            response_dict = json.loads(response.text)
        except json.decoder.JSONDecodeError as e:
            logger.exception(e)
            return {"error": "Error decoding response from Sirius"}

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

    def download_scanned_images(self, s3_urls_dict: dict) -> dict:
        """
        Downloads scanned images from S3 and saves them to a local folder.

        Args:
            s3_urls_dict: A dictionary containing URLs for scanned images in S3.

        Returns:
            A dictionary containing the local file paths of the downloaded scanned images.
        """
        # Extract the S3 URLs for the LPA and continuation sheet scans
        lpa_scan = s3_urls_dict.get('lpaScan')
        continuation_sheet_scan = s3_urls_dict.get('continuationSheetScan', None)

        # Extract the S3 locations for the scans, if they exist
        lpa_location = lpa_scan.get('location') if lpa_scan else None
        continuation_locations = continuation_sheet_scan.get('location') if continuation_sheet_scan else None

        # Download the LPA scan, if it exists
        scan_locations = {}
        if lpa_location:
            # Extract the file path and bucket name from the S3 URL
            path_parts = self.extract_s3_file_path(lpa_location)
            # Construct the local file path for the downloaded scan
            scan_location = f'{self.output_folder_path}/{path_parts["file_path"]}'
            logger.info(
                f"Attempting download from bucket: {path_parts['bucket']}, key: {path_parts['file_path']}, path: {scan_location}"
            )
            # Download the scan from S3 and save it to the local file path
            self.s3.download_file(path_parts["bucket"], path_parts["file_path"], scan_location)
            # Add the local file path to the dictionary of downloaded scan locations
            scan_locations['scan'] = scan_location

        # Download the continuation sheet scans, if they exist
        if continuation_locations and len(continuation_locations) > 0:
            location_position = 0
            for continuation_location in continuation_locations:
                # Extract the file path and bucket name from the S3 URL
                path_parts = self.extract_s3_file_path(continuation_location)
                # Construct the local file path for the downloaded scan
                scan_location = f'{self.output_folder_path}/{path_parts["file_path"]}'
                logger.info(
                    f"Attempting download from bucket: {path_parts['bucket']}, key: {path_parts['file_path']}, path: {scan_location}"
                )
                # Download the scan from S3 and save it to the local file path
                self.s3.download_file(path_parts["bucket"], path_parts["file_path"], scan_location)
                # Add the local file path to the dictionary of downloaded scan locations
                location_position += 1
                scan_locations[f'continuation_{location_position}'] = scan_location

        return scan_locations

    def extract_instructions_and_preferences(self, image_locations: dict) -> dict:
        """
        Extracts instructions and preferences from scanned images.

        Args:
            image_locations: A dictionary containing S3 bucket locations of the scanned images.

        Returns:
            A list of file paths that have been selected for upload.
        """
        # Create FormOperator instance from config file
        form_operator = FormOperator.create_from_config(f"{self.extraction_folder_path}/opg-config.yaml")
        # Generate a unique folder name based on current timestamp
        self.folder_name = self.get_timestamp_as_str()

        continuation_keys_to_use = []
        for key, image_location in image_locations.items():
            # Run full pipeline to extract data from the scanned image
            _ = form_operator.run_full_pipeline(
                form_path=image_location,
                pass_dir=f"{self.output_folder_path}/pass/{self.folder_name}/{key}",
                fail_dir=f"{self.output_folder_path}/fail/{self.folder_name}/{key}",
                form_meta_directory=f"{self.extraction_folder_path}/metadata",
            )
            # If the key contains "continuation_", add it to the list of continuation keys to use
            if 'continuation_' in key:
                continuation_keys_to_use.append(key)

        # Get the list of file paths that have been extracted from the scanned images
        paths = self.list_files(f'{self.output_folder_path}/pass/{self.folder_name}', '.jpg')
        logger.info(f"Paths: {paths}")
        # Select the paths to upload based on continuation keys
        path_selection = self.get_selected_paths_for_upload(paths, continuation_keys_to_use)

        return path_selection

    def put_images_to_bucket(self, path_selection):
        for key, value in path_selection.items():
            image = f'iap-{self.uid}-{key}'
            try:
                self.s3.put_object(
                    Bucket=self.iap_bucket,
                    Key=image,
                    Body=open(value, 'rb'),
                    ServerSideEncryption='AES256',
                    Metadata={
                        'ContinuationSheetsInstructions': str(self.continuation_instruction_count),
                        'ContinuationSheetsPreferences': str(self.continuation_preference_count)
                    }
                )
                logger.info(f"File '{image}' added to the '{self.iap_bucket}' bucket.")
            except Exception as e:
                logger.error(f"Error: Failed to add file '{image}' to the '{self.iap_bucket}' bucket. {e}")
                raise

    def find_instruction_and_preference_paths(self, path_selection: dict, paths: list) -> dict:
        """
        Searches through a dictionary of file paths to find the paths to the instructions and preferences files.
        Also detects if continuation checkboxes are marked, and sets continuation flags accordingly.

        Args:
            path_selection (Dict[str, str]): Dictionary with keys "instructions" and "preferences", which will be updated
                with the file paths to the instructions and preferences files, respectively.
            paths (List[str]): List containing file paths to search through.

        Returns:
            Dict[str, Any]: Dictionary with keys "path_selection", "continuation_instructions", and "continuation_preferences".
                "path_selection" contains the updated "instructions" and "preferences" file paths.
                "continuation_instructions" is a boolean indicating if the continuation checkbox for instructions is marked.
                "continuation_preferences" is a boolean indicating if the continuation checkbox for preferences is marked.
        """

        continuation_instructions = False
        continuation_preferences = False

        for path in paths:
            if self.string_fragments_in_string(
                    target_string=path,
                    mandatory_fragments=[
                        'field_name=preferences'
                    ],
                    one_of_fragments=[
                        'meta=lp1f',
                        'meta=lp1h'
                    ]
            ):
                path_selection['preferences'] = path
                logger.info(f'Found preferences path {path}')
            elif self.string_fragments_in_string(
                    target_string=path,
                    mandatory_fragments=[
                        'field_name=instructions'
                    ],
                    one_of_fragments=[
                        'meta=lp1f',
                        'meta=lp1h'
                    ]
            ):
                path_selection['instructions'] = path
                logger.info(f'Found instructions path {path}')
            elif self.string_fragments_in_string(
                    target_string=path,
                    mandatory_fragments=[
                        'field_name=continuation_checkbox_instructions',
                    ],
                    one_of_fragments=[
                        'meta=lp1f',
                        'meta=lp1h'
                    ]
            ):
                if self.detect_marked_checkbox(path):
                    continuation_instructions = True
            elif self.string_fragments_in_string(
                    target_string=path,
                    mandatory_fragments=[
                        'field_name=continuation_checkbox_preferences',
                    ],
                    one_of_fragments=[
                        'meta=lp1f',
                        'meta=lp1h'
                    ]
            ):
                if self.detect_marked_checkbox(path):
                    continuation_preferences = True

        logger.info(f"path selection.. {path_selection}")

        return {
            "path_selection": path_selection,
            "continuation_instructions": continuation_instructions,
            "continuation_preferences": continuation_preferences
        }

    def get_continuation_sheet_paths(self, paths, continuation_sheet_type, path_filter) -> dict:
        """
        Get the paths of the continuation sheet pages and the types of checkboxes checked
        for a single continuation sheet.

        Args:
            paths: A list of file paths to check for continuation sheets.
            continuation_sheet_type: The type of continuation sheet to look for.
            path_filter: The string to filter the file paths with.

        Returns:
            A dictionary containing the paths and types of the continuation sheet pages.
        """

        # Structure of return object defined here for clarity.
        # This is all the data we need for a single continuation sheet
        pages = {
            'p1': {
                'path': '',
                'type': ''
            },
            'p2': {
                'path': '',
                'type': ''
            }
        }

        checkboxes = {
            'preferences': {
                'p1': 'field_name=preferences_checkbox_p1',
                'p2': 'field_name=preferences_checkbox_p2'
            },
            'instructions': {
                'p1': 'field_name=instructions_checkbox_p1',
                'p2': 'field_name=instructions_checkbox_p2'
            }
        }
        checked_checkboxes = {'p1': [], 'p2': []}
        warning_message = 'Found unexpected continuation sheet type.'

        # Loops over the paths filtered by our filter.
        # Finds out which checkbox type is ticked for each page.
        # Adds the path for the actual text box for each page
        for path in paths:
            if path_filter in path:
                for page in ['p1', 'p2']:
                    for sheet_type in ['preferences', 'instructions']:
                        checkbox = checkboxes[sheet_type][page]
                        # Checks on checkbox type for each page and appends and checked boxes to a list
                        if self.string_fragments_in_string(
                                target_string=path,
                                mandatory_fragments=[checkbox],
                                one_of_fragments=['meta=lpc']
                        ):
                            if self.detect_marked_checkbox(path):
                                if continuation_sheet_type in ['BOTH', sheet_type.upper()]:
                                    checked_checkboxes[page].append(sheet_type)
                                else:
                                    logger.warning(
                                        f"{warning_message} Expected: {continuation_sheet_type}, Actual: {sheet_type}"
                                    )
                                    checked_checkboxes[page].append(sheet_type)
                        # Appends the continuation sheet text to path item of pages dict for each page
                        elif self.string_fragments_in_string(
                                target_string=path,
                                mandatory_fragments=[f'field_name=continuation_sheet_{page}'],
                                one_of_fragments=['meta=lpc']
                        ):
                            pages[page]['path'] = path

        for page in ['p1', 'p2']:
            if len(checked_checkboxes[page]) > 1:
                logger.warning(f"User has ticked more than one checkbox for page {page} of path {path_filter}")
            # Make type neither where no checkboxes ticked or the last type ticked otherwise
            pages[page]['type'] = 'neither' if not checked_checkboxes[page] else checked_checkboxes[page][-1]

        return pages

    @staticmethod
    def get_continuation_sheet_type(instructions, preferences):
        if preferences and instructions:
            return 'BOTH'
        elif instructions:
            return 'INSTRUCTIONS'
        elif preferences:
            return 'PREFERENCES'
        else:
            return 'NEITHER'

    def get_selected_paths_for_upload(self, paths, continuation_keys_to_use) -> dict:
        """
        Given a list of file paths and a list of continuation keys, returns a dictionary of selected file paths
        for upload,
        including any continuation sheets required.

        Args:
            paths (List[str]): A list of file paths to select from.
            continuation_keys_to_use (List[str]): A list of continuation keys to use for selecting continuation sheets.

        Returns:
            Dict[str, List[str]]: A dictionary containing the selected file paths for upload,
            including any continuation sheets.
        """
        # Create an empty dictionary to store the selected paths
        path_selection = {}

        # Find the instruction and preference paths
        response = self.find_instruction_and_preference_paths(path_selection, paths)

        # Extract the path selection and continuation sheet type from the response
        path_selection = response["path_selection"]
        continuation_sheet_type = self.get_continuation_sheet_type(
            response["continuation_instructions"], response["continuation_preferences"]
        )

        # Loop through each continuation key and get the corresponding continuation sheet paths
        continuation_sheets = {}
        for continuation_key in continuation_keys_to_use:
            path_filter = f'pass/{self.folder_name}/{continuation_key}'
            continuation_sheets[continuation_key] = self.get_continuation_sheet_paths(
                paths,
                continuation_sheet_type,
                path_filter
            )
        logger.info(f"Continuation_Sheets: {continuation_sheets}")

        # Created the final combined object of instructions, preferences and continuation sheets
        path_selection = self.merge_continuation_images_into_path_selection(path_selection, continuation_sheets)

        return path_selection

    def update_continuation_sheet_counts(self, paths_to_extracted_images: dict) -> None:
        """
        Updates the counts of continuation instruction and preference sheets based on the paths to extracted images.

        Args:
            paths_to_extracted_images (dict): A dictionary containing paths to extracted images.
        """
        self.continuation_instruction_count = sum(
            1 for key in paths_to_extracted_images.keys() if "continuation_instructions" in key
        )
        self.continuation_preference_count = sum(
            1 for key in paths_to_extracted_images.keys() if "continuation_preferences" in key
        )

    @staticmethod
    def merge_continuation_images_into_path_selection(path_selection, continuation_sheets) -> dict:
        """
        Merge continuation images into path selection.

        Args:
            path_selection (dict): Dictionary containing paths for preferences and instructions.
            continuation_sheets (dict): Dictionary containing continuation sheet paths and their types.

        Returns:
            dict: A dictionary containing paths for preferences, instructions, and continuation sheets.
        """

        preferences_continuation_count = 0
        instructions_continuation_count = 0
        for continuation_name, continuation_dict in continuation_sheets.items():
            for pagenumber, pagenumber_dict in continuation_dict.items():
                if pagenumber_dict["type"] == "preferences":
                    preferences_continuation_count += 1
                    key = f"continuation_preferences_{preferences_continuation_count}"
                elif pagenumber_dict["type"] == "instructions":
                    instructions_continuation_count += 1
                    key = f"continuation_instructions_{instructions_continuation_count}"
                else:
                    continue
                # Add the page path to the corresponding key in final_path_selection
                path_selection[key] = pagenumber_dict["path"]

        return path_selection

    @staticmethod
    def string_fragments_in_string(target_string, mandatory_fragments, one_of_fragments) -> bool:
        """
        Check if all mandatory fragments are present in the target string and at least one of the optional fragments is present.
        Args:
            target_string: The string to check.
            mandatory_fragments: A list of strings that must be present in the target string.
            one_of_fragments: A list of strings of which at least one must be present in the target string.

        Returns:
            True if all mandatory fragments are present and at least one of the optional fragments is present in the target string, False otherwise.
        """
        # Check if all mandatory fragments are present
        for fragment in mandatory_fragments:
            if fragment not in target_string:
                return False

        # Check if at least one of the optional fragments is present
        if not any(fragment in target_string for fragment in one_of_fragments):
            return False

        # Return True if all conditions are met
        return True

    @staticmethod
    def detect_marked_checkbox(image_path) -> bool:
        """
        Detects if a checkbox is marked in an image and returns True if it is, False otherwise.

        Args:
            image_path (str): the path to the image file

        Returns:
            bool: True if checkbox is marked, False otherwise
        """
        # Load the image in grayscale
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

        (thresh, im_bw) = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        # Mask always seems to be black so we invert so mask and background match
        im_bw_inverted = cv2.bitwise_not(im_bw)
        # Define the size of the image and the size of the border to ignore
        img_height, img_width = im_bw_inverted.shape

        border_size = int(min(img_height, img_width) * 0.2)

        # Create a mask to ignore the border
        mask = np.zeros((img_height, img_width), np.uint8)
        mask[border_size:img_height - border_size, border_size:img_width - border_size] = 255

        # Apply the mask to the image
        im_bw_inverted = cv2.bitwise_and(im_bw_inverted, im_bw_inverted, mask=mask)

        number_of_white_pix = np.sum(im_bw_inverted == 255)  # extracting only white pixels
        number_of_black_pix = np.sum(im_bw_inverted == 0)
        total_pixels = number_of_white_pix + number_of_black_pix
        percentage_black = number_of_black_pix / total_pixels

        is_ticked = False if percentage_black > 0.99 else True
        logger.info(f"Checkbox is {str(is_ticked)} for: {image_path}")

        # If the percentage_black (as image is inverted) is above a certain threshold, the image is blank
        return False if percentage_black > 0.99 else True

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


def lambda_handler(event, context):
    image_processor = ImageProcessor(event)
    image_processor.process_request()
