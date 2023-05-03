import copy
import os
import json
import re
import shutil
import datetime
import time
from collections import Counter
from pyzbar.pyzbar import decode

import jwt
import cv2
import numpy as np

import boto3
import requests
from botocore.exceptions import ClientError
from form_tools.form_operators import FormOperator
from form_tools.utils.image_reader import ImageReader
from app.utility.custom_logging import custom_logger

logger = custom_logger("processor")


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
        self.info_msg = {
            "uid": None,
            "document_paths": {},
            "matched_templates": [],
            "images_uploaded": [],
            "status": "Not Started"
        }

    def process_request(self):
        """
        Main Process that receives a request triggered from SQS and extracts the
        instructions and preferences and pushes them to S3.
        """
        try:
            self.uid = self.get_uid_from_event()
            self.info_msg["uid"] = self.uid

            logger.info(f'==== Starting processing on {self.uid} ====')
            self.create_output_dir()

            # Get response from sirius for all scanned documents in s3 bucket for given UID
            sirius_response_dict = self.make_request_to_sirius(self.uid)
            logger.debug(f'Response from Sirius: {str(sirius_response_dict)}')

            # Download all files from sirius and store their path locations
            downloaded_scan_locations = self.download_scanned_images(sirius_response_dict)
            self.info_msg["document_paths"] = downloaded_scan_locations
            logger.debug(f'Downloaded scan locations: {str(downloaded_scan_locations)}')

            # Extract all relevant images relating to instructions and preferences from downloaded documents
            paths_to_extracted_images = self.extract_instructions_and_preferences(downloaded_scan_locations)
            logger.debug(f"Paths to extracted images: {paths_to_extracted_images}")

            # Update the counts that will be pushed as metadata
            self.update_continuation_sheet_counts(paths_to_extracted_images)
            logger.debug("Updated continuation sheet counts")

            # Push images up to the buckets
            self.put_images_to_bucket(paths_to_extracted_images)
            logger.debug("Finished pushing images to bucket")

            # Cleanup all the folders
            self.cleanup(downloaded_scan_locations)
            logger.debug("Cleaned down paths")

            self.info_msg["status"] = "Completed"
            logger.info(self.info_msg)
        except Exception as e:
            self.info_msg["status"] = "Error"
            logger.info(self.info_msg)
            logger.error(e)

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
        try:
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
        except Exception as e:
            raise Exception(f"Failed to create output directory: {e}")

    def cleanup(self, downloaded_document_locations):
        """
        Cleans up downloaded images and removes the pass and fail directories created during the image processing.
        Also removes any pdfs older than one hour and any pass and fail folders older than 1 hour.

        Args:
        - downloaded_image_locations (dict): A dictionary containing the paths to the downloaded images.
        """
        downloaded_document_paths = []
        # Extract the paths from the 'scans' key and add them to the list
        if "scans" in downloaded_document_locations:
            for path in downloaded_document_locations['scans']:
                downloaded_document_paths.append(path)

        # Extract the paths from the 'continuations' keys and add them to the list
        if "continuations" in downloaded_document_locations:
            for key, value in downloaded_document_locations['continuations'].items():
                downloaded_document_paths.append(value)

        # Remove downloaded images
        for path in downloaded_document_paths:
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

    def get_uid_from_event(self):
        try:
            message = self.event['Records'][0]['body']
            # Parse the message and get the uid value
            message_dict = json.loads(message)
            uid = message_dict['uid']
        except KeyError:
            raise Exception("UID key exception in event body")
        except json.decoder.JSONDecodeError:
            raise Exception("Problem loading JSON from event body")
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
        logger.debug(f"Sending request to Sirius on url: {url}")

        try:
            response = requests.get(url=url, headers=headers)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error getting response from Sirius: {e}")

        try:
            response_dict = json.loads(response.text)
        except json.decoder.JSONDecodeError as e:
            raise Exception(f"Unable to decode sirius JSON: {e}")

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
        # Extract the S3 URLs for the possible LPA sheet scans
        lpa_scan = s3_urls_dict.get('lpaScans')
        lpa_locations = lpa_scan.get('locations') if lpa_scan else None

        # Extract the S3 locations for the possible continuation sheet scans, if they exist
        continuation_sheet_scan = s3_urls_dict.get('continuationSheetScans', None)
        continuation_locations = continuation_sheet_scan.get('locations') if continuation_sheet_scan else None

        # Download the LPA scan, if it exists
        scan_locations = {}
        if not lpa_locations or len(lpa_locations) == 0:
            raise Exception(f"No documents returned by Sirius. Sirius response dictionary: {s3_urls_dict}")

        scan_locations['scans'] = []
        scan_locations['continuations'] = {}
        for lpa_location in lpa_locations:
            try:
                # Extract the file path and bucket name from the S3 URL
                path_parts = self.extract_s3_file_path(lpa_location)
                # Construct the local file path for the downloaded scan
                scan_location = f'{self.output_folder_path}/{path_parts["file_path"]}'
                logger.debug(
                    f"Attempting download from bucket: {path_parts['bucket']}, key: {path_parts['file_path']}, path: {scan_location}"
                )
                # Download the scan from S3 and save it to the local file path
                self.s3.download_file(path_parts["bucket"], path_parts["file_path"], scan_location)
                # Add the local file path to the dictionary of downloaded scan locations
                scan_locations['scans'].append(scan_location)
            except Exception as e:
                raise Exception(f"Error downloading scanned document {lpa_location}: {e}")

        # Download the continuation sheet scans, if they exist
        if not continuation_locations or len(continuation_locations) == 0:
            return scan_locations

        location_position = 0
        for continuation_location in continuation_locations:
            try:
                # Extract the file path and bucket name from the S3 URL
                path_parts = self.extract_s3_file_path(continuation_location)
                # Construct the local file path for the downloaded scan
                scan_location = f'{self.output_folder_path}/{path_parts["file_path"]}'
                logger.debug(
                    f"Attempting download from bucket: {path_parts['bucket']}, key: {path_parts['file_path']}, path: {scan_location}"
                )
                # Download the scan from S3 and save it to the local file path
                self.s3.download_file(path_parts["bucket"], path_parts["file_path"], scan_location)
                # Add the local file path to the dictionary of downloaded scan locations
                location_position += 1
                scan_locations['continuations'][f'continuation_{location_position}'] = scan_location
            except Exception as e:
                raise Exception(f"Error downloading scanned continuation sheet {continuation_location}: {e}")

        return scan_locations

    def extract_instructions_and_preferences(self, scan_locations: dict) -> dict:
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

        # Run full pipeline to extract data from the scanned image
        continuation_keys_to_use = self.run_iap_extraction(
            scan_locations=scan_locations,
            form_operator=form_operator
        )

        # Get the list of file paths that have been extracted from the scanned images
        paths = self.list_files(f'{self.output_folder_path}/pass/{self.folder_name}', '.jpg')
        logger.debug(f"Full list of paths extracted from scanned images: {paths}")
        # Select the paths to upload based on continuation keys
        path_selection = self.get_selected_paths_for_upload(paths, continuation_keys_to_use)

        return path_selection

    @staticmethod
    def get_preprocessed_images(form_path, form_operator):
        logger.debug(f"Reading form from path: {form_path}")
        _, imgs = ImageReader.read(form_path)

        logger.debug("Pre-processing raw form images...")
        preprocessed_imgs = form_operator.preprocess_form_images(imgs)

        logger.debug("Auto-rotating images based on text direction...")
        rotated_images = form_operator.auto_rotate_form_images(preprocessed_imgs)

        logger.debug(f"Total images found: {len(rotated_images)}")

        return rotated_images

    def get_ocr_matches(
            self, processed_images: list, form_operator: FormOperator, form_meta_directory: str
    ) -> dict:
        """
        Applies OCR to extract text from images, filters metadata by matching form regex,
        and attempts to identify matches based on text identification.

        Args:
            - processed_images (List[Any]): A list of processed images to extract text from.
            - form_operator (Any): A form operator object with `form_images_to_text` method.
            - form_meta_directory (str): A directory containing form metadata documents.

        Returns:
            - matched_items (Dict[str, Any]): A dictionary containing the results of the matching process.
              The dictionary contains keys:
              - 'image_page_map' (Dict[Tuple[int, int], List[int]]): A dictionary mapping a tuple of
                (form_index, image_index) to a list of matched page indices in metadata documents.
              - 'match_confidences' (List[float]): A list of match confidences for all matched items.
        """
        logger.debug("Increase image size to help OCR...")
        form_images_doubled = self.double_image_size(processed_images)
        logger.debug("Applying OCR to extract text from images...")
        form_images_text = form_operator.form_images_to_text(form_images_doubled)
        logger.debug("Filtering metadata store by form regex...")
        # this is based on matching the form regex to filter down the number of matching metadata docs
        matching_meta_store = self.match_first_form_image_text_to_form_meta(
            form_meta_directory, form_images_text, form_operator
        )
        logger.debug(f"Created following metadata store based on form regex: {matching_meta_store}")

        logger.debug("Attempting to identify matches based on text identification")
        matched_items = self.mixed_mode_page_identifier(
            form_images_text, matching_meta_store, processed_images
        )
        logger.debug(f"Total matched based on OCR: {len(matched_items['image_page_map'])}")

        return matched_items

    @staticmethod
    def extract_images(
            matched_items: dict,
            meta: dict,
            meta_id: str,
            form_operator: FormOperator,
            scan_path: str,
            pass_dir: str,
            fail_dir: str,
            run_timestamp: str
    ) -> None:
        """
        Extracts images and fields from a form, aligns them to a metadata template, and saves the result
        in the pass directory. If there is an error, saves a copy in the fail directory.

        Parameters:
            matched_items (dict): A dictionary with information about the matched items.
            meta (dict): A dictionary with metadata for the form.
            meta_id (str): The ID of the metadata template to use.
            form_operator (object): The operator to use for the form.
            scan_path (str): The path to the form.
            pass_dir (str): The directory to save the result in.
            fail_dir (str): The directory to save a copy in if there is an error.
            run_timestamp (str): The timestamp of the run.

        Returns:
            None
        """
        encode_type = ".jpg"

        try:
            # Align the images to the metadata template
            logger.debug("Aligning images...")
            aligned_images = form_operator.align_images_to_template(
                matched_items["image_page_map"], form_meta=meta, debug=False
            )

            # Extract the fields from the form images
            logger.debug(f"Selected template is: {meta_id}")
            logger.debug("Extracting fields from form images...")
            extracted_fields = form_operator.extract_fields(
                aligned_images,
                form_meta=meta,
                as_bytes=False,
                encode_type=encode_type,
                debug=False,
            )

            # Write the extracted fields to the pass directory
            logger.debug("Writing to pass directory...")
            form_operator._write_to_pass(
                extracted_fields=extracted_fields,
                original_path=scan_path,
                pass_dir=pass_dir,
                meta_id=meta_id,
                timestamp=run_timestamp,
                as_bytes=False,
                encode_type=".jpg",
            )

        except Exception as e:
            # If there is an error, save a copy in the fail directory
            logger.debug(f"Failed to match doc to a metadata template {scan_path}: {e}")
            logger.debug("Saving copy in fail directory")
            form_operator._copy_to_fail(
                form_path=scan_path,
                fail_dir=fail_dir,
                meta_id="unknown",
                timestamp=run_timestamp,
            )

    def get_matching_continuation_items(
            self, scan_locations: dict, form_meta_directory: str, form_operator: FormOperator) -> dict:
        """
        This function attempts to match continuation scan locations with corresponding items using barcodes and OCR.

        :param scan_locations: Dictionary containing scan locations of the form.
        :param form_meta_directory: Directory containing the form meta data.
        :param form_operator: Operator for handling form data.
        :return: Dictionary containing matched continuation documents.
        """
        matched_lpa_scans_store = {}

        # Loop through scan locations and attempt to match them
        for key, scan_location in scan_locations['continuations'].items():
            # Get preprocessed images for current scan location
            processed_images = self.get_preprocessed_images(scan_location, form_operator)

            # Get form meta data
            matching_meta_store = form_operator.form_meta_store(form_meta_directory)

            logger.debug(f"Attempting to match {scan_location} based on barcodes...")
            # Attempt to match based on barcodes
            matched_items = self.find_matches_from_barcodes(processed_images, matching_meta_store)
            logger.debug(f"Barcode matches for {scan_location}: {len(matched_items['image_page_map'])}")

            # If no matches found using barcodes, attempt to match using OCR
            if len(matched_items['image_page_map']) == 0:
                logger.debug(f"Attempting to match {scan_location} based on OCR...")
                matched_items = self.get_ocr_matches(processed_images, form_operator, form_meta_directory)

            # If matches found, store them in the matched LPA scans store
            if len(matched_items["image_page_map"]) > 0:
                if 'continuation_' in key:
                    matched_lpa_scans_store[key] = {}
                    matched_lpa_scans_store[key]["match"] = matched_items
                    matched_lpa_scans_store[key]["scan_location"] = scan_location

        logger.debug(f"Matched continuation documents: {len(matched_lpa_scans_store)}")

        return matched_lpa_scans_store

    def get_matching_scan_item(
            self,
            scan_locations: dict,
            complete_meta_store: dict,
            form_meta_directory: str,
            form_operator: FormOperator
    ) -> dict:
        """
        Find the matching scan item from a list of scan locations by attempting to match based on barcodes and OCR.
        Returns a dictionary containing the match and the scan location.
        """
        matched_lpa_scans_store = {
            "scan": {
                "match": {},
                "scan_location": ""
            }
        }
        matches = []
        # Attempt to match based on barcodes
        for scan_location in scan_locations['scans']:
            processed_images = self.get_preprocessed_images(scan_location, form_operator)
            logger.debug(f"Attempting to match {scan_location} based on barcodes...")
            matched_items = self.find_matches_from_barcodes(processed_images, complete_meta_store)
            logger.debug(f"Barcode matches for {scan_location}: {len(matched_items['image_page_map'])}")
            if len(matched_items['image_page_map']) > 0:
                matched_lpa_scans_store[f"scan"]["match"] = matched_items
                matched_lpa_scans_store[f"scan"]["scan_location"] = scan_location
                matched_lpa_scans_store_deep = copy.deepcopy(matched_lpa_scans_store)
                matches.append(matched_lpa_scans_store_deep)

        # Check if there is exactly one match
        logger.debug(f"Matched LPA scan documents based on barcodes: {len(matches)}")
        if len(matches) > 1:
            raise Exception("More than one matching document path for LPA barcode scans")
        elif len(matches) == 1:
            return matched_lpa_scans_store

        # Attempt to match based on OCR
        logger.debug("Attempting to match scans based on OCR...")
        for scan_location in scan_locations['scans']:
            processed_images = self.get_preprocessed_images(scan_location, form_operator)
            matched_items = self.get_ocr_matches(processed_images, form_operator, form_meta_directory)
            if len(matched_items["image_page_map"]) > 0:
                matched_lpa_scans_store["scan"]["match"] = matched_items
                matched_lpa_scans_store["scan"]["scan_location"] = scan_location
                matched_lpa_scans_store_deep = copy.deepcopy(matched_lpa_scans_store)
                matches.append(matched_lpa_scans_store_deep)

        # Check if there is exactly one match
        logger.debug(f"Matched LPA scan documents based on OCR: {len(matches)}")
        if len(matches) > 1:
            raise Exception("More than one matching document path for LPA OCR scans")
        elif len(matches) == 1:
            return matches[0]

    def run_iap_extraction(
            self,
            scan_locations: dict,
            form_operator: FormOperator,
    ):
        continuation_keys_to_use = []
        run_timestamp = int(datetime.datetime.utcnow().timestamp())
        form_meta_directory = f"{self.extraction_folder_path}/metadata"
        complete_meta_store = form_operator.form_meta_store(form_meta_directory)

        # Find matches based on Scans (only one should match)
        scan_sheet_store = self.get_matching_scan_item(
            scan_locations, complete_meta_store, form_meta_directory, form_operator
        )

        # Find matches based on Continuation sheets (multiple matches possible)
        continuation_sheet_store = self.get_matching_continuation_items(
            scan_locations, form_meta_directory, form_operator
        )

        complete_matching_store = {**scan_sheet_store, **continuation_sheet_store}

        if len(complete_matching_store) == 0:
            raise Exception("No matches found in any documents")

        for key, matched_document_store_item in complete_matching_store.items():
            pass_dir = f"{self.output_folder_path}/pass/{self.folder_name}/{key}"
            fail_dir = f"{self.output_folder_path}/fail/{self.folder_name}/{key}"
            meta_id = matched_document_store_item["match"]["meta_id"]
            meta = complete_meta_store[meta_id]
            document_path = matched_document_store_item["scan_location"]
            matched_document_items = matched_document_store_item["match"]
            self.extract_images(
                matched_document_items, meta, meta_id, form_operator, document_path, pass_dir, fail_dir, run_timestamp
            )

            # If the key contains "continuation_", add it to the list of continuation keys to use
            if 'continuation_' in key:
                continuation_keys_to_use.append(key)

        return continuation_keys_to_use

    @staticmethod
    def double_image_size(image_list: list) -> list:
        """
        Takes in a list of NumPy arrays representing images, doubles the size of each image,
        and returns the new list of NumPy arrays with the doubled-sized images.
        """
        # Create an empty list to store the new images
        doubled_images = []

        # Loop through each image in the input list
        for image in image_list:
            # Get the current size of the image
            height, width = image.shape[:2]
            image = cv2.resize(image, (round(2 * width), round(2 * height)), interpolation=cv2.INTER_LANCZOS4)
            doubled_images.append(image)

        # Return the list of doubled-size images
        return doubled_images

    def find_matches_from_barcodes(
            self,
            images: list,
            form_metastore: dict
    ) -> dict:
        """
        Finds and matches barcodes in the input images to the corresponding template pages in the
        form metastore.

        Args:
            images (List[np.ndarray]): A list of images to be matched with templates.
            form_metastore (Dict[str, Any]): A dictionary containing form template metadata.

        Returns:
            Union[Dict[str, Any], List[Dict[str, Any]]]: If a match is found, a dictionary containing
            the metadata of the form template and a mapping between template pages and images. If no
            matches are found, an empty dictionary is returned. If too many matches are found, a
            dictionary with an empty image-page map is returned. If multiple matches are found, a list
            of dictionaries with the metadata and image-page mappings for each matched template is
            returned.
        """
        img_count = 0
        image_barcode_dict = {}
        matched_meta = {
            "meta_id": "",
            "image_page_map": {}
        }

        # Iterate over each image and find its barcode
        for img in images:
            height, width = img.shape[:2]
            roi = img[0:height // 3, 2 * width // 3:width]
            barcodes = decode(roi)

            barcodes_decoded = []
            for barcode in barcodes:
                barcodes_decoded.append(barcode.data.decode('utf-8'))

            if len(barcodes_decoded) > 0:
                image_barcode_dict[img_count] = barcodes_decoded[0]

            img_count += 1

        # Iterate over each form in the form_metastore and try to match it to an image by its barcode
        matching_images = []
        for meta_id, meta in form_metastore.items():
            matching_image_page = {}
            images_used = []
            form_pages_used = []

            for form_page in meta.form_pages:
                template_barcode = form_page.additional_args['extra']["barcode"]

                for img_count, image_barcode in image_barcode_dict.items():
                    if template_barcode == image_barcode:
                        # Check that we haven't already matched this image or form page
                        if img_count not in images_used and form_page.page_number not in form_pages_used:
                            logger.debug(
                                f"Barcode match on {template_barcode} for image {img_count} from page: {form_page.page_number}")
                            matching_image_page[form_page.page_number] = [images[img_count]]
                            images_used.append(img_count)
                            form_pages_used.append(form_page.page_number)
                            self.info_msg["matched_templates"].append(
                                f"Match on {meta_id } with barcode {template_barcode} "
                                f"for scan page number {img_count} from template page {form_page.page_number}"
                            )

            matched_meta["meta_id"] = meta_id
            matched_meta["image_page_map"] = matching_image_page

            if len(matched_meta["image_page_map"]) > 0:
                matched_meta_deep = copy.deepcopy(matched_meta)
                matching_images.append(matched_meta_deep)

        # Handle the cases where we have too many or too few matches
        if len(matching_images) > 1:
            logger.debug("Too many matches on Barcodes")
            matched_meta["image_page_map"] = {}
            return matched_meta

        if len(matching_images) == 0:
            logger.debug("No matches on barcodes")
            return matched_meta

        # If we have exactly one match, return it
        return matching_images[0]

    def create_scan_to_template_distances(self, form_images_as_strings, form_metastore):
        scan_to_template_distances = []
        for meta_id, meta in form_metastore.items():
            for form_page in meta.form_pages:
                meta_page_text = self.get_meta_page_text(form_page)
                for scan_page_no, form_image_as_string in enumerate(form_images_as_strings, start=1):
                    distance = self.calculate_levenstein_distance(form_page, form_image_as_string, meta_page_text)
                    scan_info = {
                        "meta": meta_id,
                        "distance": distance,
                        "scan_page_no": scan_page_no,
                        "template_page_no": form_page.page_number,
                        "form_image_as_string": form_image_as_string,
                        "meta_page_text": meta_page_text,
                    }
                    scan_to_template_distances.append(scan_info)
        return scan_to_template_distances

    def get_meta_page_text(self, form_page):
        template_page_text_file = f"{self.extraction_folder_path}/target_texts/{form_page.additional_args['extra']['page_text']}"
        with open(template_page_text_file, 'r') as file:
            meta_page_text = file.read().replace('\n', '')
        return meta_page_text

    def calculate_levenstein_distance(self, form_page, form_image_as_string, meta_page_text):
        page_regex = form_page.identifier
        regex_match = True if re.search(page_regex, form_image_as_string, re.DOTALL) is not None else False
        if regex_match:
            distance = self.levenstein_distance(form_image_as_string, meta_page_text)
        else:
            distance = 1000
        return distance

    def get_similarity_score(self, sorted_scan_template_entities):
        similarity_score = self.similarity_score(
            sorted_scan_template_entities[0]["meta_page_text"],
            sorted_scan_template_entities[0]["form_image_as_string"]
        )
        logger.debug(f"Top similarity score is: {similarity_score}")
        return similarity_score

    @staticmethod
    def get_meta_id_to_use(sorted_scan_template_entities):
        meta_id_to_use = sorted_scan_template_entities[0]['meta']
        return meta_id_to_use

    def get_matching_image_results(self, meta_id_to_use, similarity_score, sorted_scan_template_entities, form_images):
        matching_image_results = {"meta_id": meta_id_to_use, "image_page_map": {}}
        if similarity_score < 0.7:
            return matching_image_results
        template_pages_used = set()
        scan_pages_used = set()
        templates_to_keep = []
        for scan_template_entity in sorted_scan_template_entities:
            template_page_no = scan_template_entity['template_page_no']
            scan_page_no = scan_template_entity['scan_page_no']
            meta_id = scan_template_entity['meta']
            if template_page_no not in template_pages_used and scan_page_no not in scan_pages_used and meta_id == meta_id_to_use:
                scan_pages_used.add(scan_page_no)
                template_pages_used.add(template_page_no)
                templates_to_keep.append(scan_template_entity)

        for template_to_keep in templates_to_keep:
            template_page_no = template_to_keep['template_page_no']
            scan_page_no = template_to_keep['scan_page_no']
            matching_image_results["image_page_map"].setdefault(template_page_no, []).append(
                form_images[scan_page_no - 1])
            self.info_msg["matched_templates"].append(
                f"Match on {meta_id_to_use} with OCR match "
                f"for scan page number {scan_page_no} from template page number {template_page_no}"
            )
        return matching_image_results

    def mixed_mode_page_identifier(self, form_images_as_strings: list, form_metastore: dict, form_images: list) -> dict:
        scan_to_template_distances = self.create_scan_to_template_distances(form_images_as_strings, form_metastore)
        sorted_scan_template_entities = sorted(scan_to_template_distances,
                                               key=lambda x: (x['distance'], x['template_page_no'], x['scan_page_no']))
        similarity_score = self.get_similarity_score(sorted_scan_template_entities)
        meta_id_to_use = self.get_meta_id_to_use(sorted_scan_template_entities)
        matching_image_results = self.get_matching_image_results(
            meta_id_to_use, similarity_score, sorted_scan_template_entities, form_images
        )
        return matching_image_results

    @staticmethod
    def levenstein_distance(source_string: str, target_string: str) -> int:
        """
        Computes the Levenstein distance between the contents of two text files.
        """
        # Read in the contents of both files
        # Create a matrix to store the Levenstein distances
        m = [[0] * (len(target_string) + 1) for _ in range(len(source_string) + 1)]

        # Initialize the first row and column of the matrix
        for i in range(len(source_string) + 1):
            m[i][0] = i

        for j in range(len(target_string) + 1):
            m[0][j] = j

        # Compute the Levenstein distance using dynamic programming
        for i in range(1, len(source_string) + 1):
            for j in range(1, len(target_string) + 1):
                if source_string[i - 1] == target_string[j - 1]:
                    m[i][j] = m[i - 1][j - 1]
                else:
                    m[i][j] = 1 + min(m[i - 1][j], m[i][j - 1], m[i - 1][j - 1])

        # Return the final Levenstein distance
        return m[-1][-1]

    @staticmethod
    def match_first_form_image_text_to_form_meta(
        form_meta_directory: str, form_images_as_strings: list, form_operator: FormOperator
    ) -> dict:
        """Filters form meta directory using given form image string
        of first page

        Loops through `FormMetadata` objects in a given directory
        and only returns those where the given form images
        contains the given metadata's identifier

        Params:
            form_meta_directory (str):
                The local path to the directory containing
                `FormMetadata` compliant json files
            form_images_as_strings (List[str]):
                List of recognised text from a set of form images

        Return:
            (Dict[str, FormMetadata]):
                A dictionary of `FormMetadata` objects
        """
        results = {}
        for id, meta in form_operator.form_meta_store(form_meta_directory).items():
            valid, _ = form_operator.form_identifier_match([form_images_as_strings[0]], meta)
            if valid:
                results[id] = meta
        return results

    @staticmethod
    def similarity_score(str1, str2):
        # remove non-alphanumeric characters and split into words
        words1 = re.findall(r'\w+', str1.lower())
        words2 = re.findall(r'\w+', str2.lower())

        # count the occurrence of each word in both strings
        word_count1 = Counter(words1)
        word_count2 = Counter(words2)

        # calculate the number of common words in both strings
        common_words_count = sum((word_count1 & word_count2).values())

        # calculate the number of unique words in each string separately
        unique_words_count1 = len(set(words1) - set(words2))
        unique_words_count2 = len(set(words2) - set(words1))

        # calculate the total number of unique words in both strings
        unique_words_count = (unique_words_count1 + unique_words_count2) / 2

        # calculate the similarity score
        similarity = common_words_count / (common_words_count + unique_words_count)

        return similarity

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
                logger.debug(f"File '{image}' added to the '{self.iap_bucket}' bucket.")
                self.info_msg["images_uploaded"].append(image)
            except Exception as e:
                raise Exception(f"Failed to add file '{image}' to the '{self.iap_bucket}' bucket: {e}")

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
                        'meta=lp1h',
                        'meta=pfa117',
                        'meta=hw114'
                    ]
            ):
                path_selection['preferences'] = path
                logger.debug(f'Found preferences path {path}')
            elif self.string_fragments_in_string(
                    target_string=path,
                    mandatory_fragments=[
                        'field_name=instructions'
                    ],
                    one_of_fragments=[
                        'meta=lp1f',
                        'meta=lp1h',
                        'meta=pfa117',
                        'meta=hw114'
                    ]
            ):
                path_selection['instructions'] = path
                logger.debug(f'Found instructions path {path}')
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
        instructions_and_preferences = self.find_instruction_and_preference_paths(path_selection, paths)
        logger.debug(f"List of IaP paths found: {instructions_and_preferences['path_selection']}")

        # Extract the path selection and continuation sheet type from the instructions_and_preferences
        path_selection = instructions_and_preferences["path_selection"]
        continuation_sheet_type = self.get_continuation_sheet_type(
            instructions_and_preferences["continuation_instructions"], instructions_and_preferences["continuation_preferences"]
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
        logger.debug(f"List of Continuation sheets found: {continuation_sheets}")

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
        logger.debug(f"Checkbox is {str(is_ticked)} for: {image_path}")

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
            raise Exception(f"Unable to get secret for JWT key from Secrets Manager: {e}")

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
