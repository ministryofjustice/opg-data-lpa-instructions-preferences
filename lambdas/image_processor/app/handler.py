import os
import json
import shutil
import datetime
import time

from app.utility.custom_logging import custom_logger

from app.utility.bucket_manager import BucketManager
from app.utility.sirius_service import SiriusService
from app.utility.extraction_service import ExtractionService

logger = custom_logger("processor")


class ImageProcessor:
    def __init__(self, event):
        self.environment = os.getenv("ENVIRONMENT")
        self.event = event
        self.extraction_folder_path = "extraction"
        self.output_folder_path = "/tmp/output"
        self.folder_name = self.get_timestamp_as_str()
        self.continuation_instruction_count = 0
        self.continuation_preference_count = 0
        self.continuation_unknown_count = 0
        self.uid = ""
        self.info_msg = {
            "uid": "",
            "document_paths": {},
            "matched_templates": [],
            "images_uploaded": [],
            "status": "Not Started",
        }

    def process_request(self):
        """
        Main Process that receives a request triggered from SQS and extracts the
        instructions and preferences and pushes them to S3.
        """
        bucket_manager = BucketManager()
        sirius_service = SiriusService(environment=self.environment)
        extraction_service = ExtractionService(
            extraction_folder_path=self.extraction_folder_path,
            folder_name=self.folder_name,
            output_folder_path=self.output_folder_path
        )
        try:
            self.uid = self.get_uid_from_event()
            self.info_msg["uid"] = self.uid

            logger.info(f"==== Starting processing on {self.uid} ====")
            self.create_output_dir()

            # Get response from sirius for all scanned documents in s3 bucket for given UID
            sirius_response_dict = sirius_service.make_request_to_sirius(self.uid)
            logger.debug(f"Response from Sirius: {str(sirius_response_dict)}")

            # Download all files from sirius and store their path locations
            downloaded_scan_locations = bucket_manager.download_scanned_images(
                sirius_response_dict, self.output_folder_path
            )
            self.info_msg["document_paths"] = downloaded_scan_locations
            logger.debug(f"Downloaded scan locations: {str(downloaded_scan_locations)}")

            # Extract all relevant images relating to instructions and preferences from downloaded documents
            paths_to_extracted_images = extraction_service.extract_instructions_and_preferences(
                downloaded_scan_locations
            )
            logger.debug(f"Paths to extracted images: {paths_to_extracted_images}")

            # Update the counts that will be pushed as metadata
            self.update_continuation_sheet_counts(paths_to_extracted_images)
            logger.debug("Updated continuation sheet counts")

            # Push images up to the buckets
            uploaded_images = bucket_manager.put_images_to_bucket(
                path_selection=paths_to_extracted_images,
                uid=self.uid,
                continuation_instruction_count=self.continuation_instruction_count,
                continuation_preference_count=self.continuation_preference_count,
                continuation_unknown_count=self.continuation_unknown_count
            )
            logger.debug("Finished pushing images to bucket")
            self.info_msg["images_uploaded"] = uploaded_images

            # Cleanup all the folders
            self.cleanup(downloaded_scan_locations)
            logger.debug("Cleaned down paths")

            self.info_msg["status"] = "Completed"
            logger.info(json.dumps(self.info_msg))
        except Exception as e:
            self.info_msg["status"] = "Error"
            logger.info(json.dumps(self.info_msg))
            logger.error(e)
            bucket_manager.put_error_image_to_bucket(self.uid)

    @staticmethod
    def get_timestamp_as_str() -> str:
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

    def cleanup(self, downloaded_document_locations) -> None:
        """
        Cleans up downloaded images and removes the pass and fail directories created during the image processing.
        Also removes any pdfs older than one hour and any pass and fail folders older than 1 hour.

        Args:
        - downloaded_image_locations (dict): A dictionary containing the paths to the downloaded images.
        """
        downloaded_document_paths = []
        # Extract the paths from the 'scans' key and add them to the list
        if "scans" in downloaded_document_locations:
            for path in downloaded_document_locations["scans"]:
                downloaded_document_paths.append(path)

        # Extract the paths from the 'continuations' keys and add them to the list
        if "continuations" in downloaded_document_locations:
            for key, value in downloaded_document_locations["continuations"].items():
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
            if os.path.isfile(file_path) and file_name.endswith(".pdf"):
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

    def get_uid_from_event(self) -> str:
        try:
            message = self.event["Records"][0]["body"]
            # Parse the message and get the uid value
            message_dict = json.loads(message)
            uid = message_dict["uid"]
        except KeyError:
            raise Exception("UID key exception in event body")
        except json.decoder.JSONDecodeError:
            raise Exception("Problem loading JSON from event body")
        return uid

    def update_continuation_sheet_counts(self, paths_to_extracted_images: dict) -> None:
        """
        Updates the counts of continuation instruction and preference sheets based on the paths to extracted images.

        Args:
            paths_to_extracted_images (dict): A dictionary containing paths to extracted images.
        """
        self.continuation_instruction_count = sum(
            1
            for key in paths_to_extracted_images.keys()
            if "continuation_instructions" in key
        )
        self.continuation_preference_count = sum(
            1
            for key in paths_to_extracted_images.keys()
            if "continuation_preferences" in key
        )
        self.continuation_unknown_count = sum(
            1
            for key in paths_to_extracted_images.keys()
            if "continuation_unknown" in key
        )


def lambda_handler(event, context):
    image_processor = ImageProcessor(event)
    image_processor.process_request()
