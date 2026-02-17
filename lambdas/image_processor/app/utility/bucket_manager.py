import os
import boto3
from app.utility.custom_logging import custom_logger

logger = custom_logger("bucket_manager")


class ScanLocation:
    def __init__(self, template: str = "", location: str = ""):
        self.__template = template
        self.__location = location

    @property
    def template(self) -> str:
        return self.__template

    @property
    def location(self) -> str:
        return self.__location

    def set_location(self, location):
        self.__location = location


class ScanLocationStore:
    def __init__(self, scans: ScanLocation = None, continuations: ScanLocation = None):
        if continuations is None:
            continuations = {}
        if scans is None:
            scans = []
        self.scans = scans
        self.continuations = continuations

    def add_scan(self, scan: ScanLocation):
        self.scans.append(scan)

    def add_continuation(self, key: str, continuation: ScanLocation):
        self.continuations[key] = continuation


class BucketManager:
    def __init__(self, info_msg):
        self.environment = os.getenv("ENVIRONMENT")
        self.target_environment = os.getenv("TARGET_ENVIRONMENT")
        self.sirius_bucket = f"opg-backoffice-datastore-{self.target_environment}"
        self.iap_bucket = f"lpa-iap-{self.environment}"
        self.s3 = self.setup_s3_connection()
        self.info_msg = info_msg

    def setup_s3_connection(self) -> boto3.client:
        """
        Sets up an S3 connection object based on the environment specified by the instance variable "environment".
        If the environment is "local", the connection object will use the local endpoint URL for testing purposes.

        Returns:
        - An S3 connection object (boto3.client).
        """
        if self.environment == "local":
            s3 = boto3.client(
                "s3",
                endpoint_url="http://localstack-request-handler:4566",
                region_name="eu-west-1",
            )
        else:
            s3 = boto3.client("s3", region_name="eu-west-1")
        return s3

    @staticmethod
    def extract_s3_file_path(s3_path: str) -> dict:
        """
        Extracts the file path from an S3 path.

        Args:
            s3_path (str): The S3 path to extract the file path from.

        Returns:
            The file path and bucket portion of the S3 path as dict.
        """
        # Remove the s3:// prefix and split the path into its components.
        path_components = s3_path[len("s3://") :].split("/", 1)
        bucket = path_components[0]

        # The first component is the bucket name, so we only need the second component.
        if len(path_components) == 2:
            file_path = path_components[1]
        else:
            file_path = ""

        return {"bucket": bucket, "file_path": file_path}

    @staticmethod
    def reorder_list_by_relevance(scan_list: list) -> list:
        def key_func(item):
            template = item.template
            if template and template.startswith("LPA"):
                return 0
            elif template is not None and template != "":
                return 1
            else:
                return 2

        return sorted(scan_list, key=key_func)

    def download_scanned_images(
        self, s3_urls_dict: dict, output_folder_path: str
    ) -> ScanLocationStore:
        """
        Downloads scanned images from S3 and saves them to a local folder.

        Args:
            s3_urls_dict: A dictionary containing URLs for scanned images in S3.
            output_folder_path: Path to base output folder for s3 downloads

        Returns:
            A dictionary containing the local file paths of the downloaded scanned images.
        """
        # Extract the S3 URLs for the possible LPA sheet scans
        lpa_scans = s3_urls_dict.get("lpaScans", [])
        lpa_locations = []
        for lpa_scan in lpa_scans:
            try:
                # lpa_scan["template"] is sourced from the sirius field "sourceDocumentType"
                # PoaNotes attached to cases are not stored with a "sourceDocumentType" so "template"
                # does not exist in these cases.
                template_type = lpa_scan.get("template")
                if template_type is None:
                    logger.info(
                        f"Template not provided for scan location: {lpa_scan}"
                    )
                    continue

                scan_location = ScanLocation(
                    location=lpa_scan["location"], template=template_type
                )
                lpa_locations.append(scan_location)
                self.info_msg.document_templates.append(scan_location.template)
            except KeyError as e:
                raise Exception(f"Error adding scan location: {e}")

        lpa_locations_reordered = self.reorder_list_by_relevance(lpa_locations)

        # Extract the S3 locations for the possible continuation sheet scans, if they exist
        continuation_sheet_scans = s3_urls_dict.get("continuationSheets", [])
        continuation_locations = []
        for continuation_sheet_scan in continuation_sheet_scans:
            continuation_location = ScanLocation(
                location=continuation_sheet_scan["location"],
                template=continuation_sheet_scan["template"],
            )
            continuation_locations.append(continuation_location)
            self.info_msg.document_templates.append(continuation_location.template)

        # Download the LPA scan, if it exists
        if not lpa_locations_reordered or len(lpa_locations_reordered) == 0:
            raise Exception(
                "No documents returned by Sirius. Sirius response dictionary"
            )

        scan_locations = ScanLocationStore()
        for lpa_location in lpa_locations_reordered:
            try:
                # Extract the file path and bucket name from the S3 URL
                path_parts = self.extract_s3_file_path(lpa_location.location)
                # Construct the local file path for the downloaded scan
                scan_location = f'{output_folder_path}/{path_parts["file_path"]}'
                logger.debug(
                    f"Attempting download from bucket: {path_parts['bucket']}, "
                    f"key: {path_parts['file_path']}, path: {scan_location}"
                )
                # Download the scan from S3 and save it to the local file path
                self.s3.download_file(
                    path_parts["bucket"], path_parts["file_path"], scan_location
                )
                # Add the local file path to the dictionary of downloaded scan locations
                lpa_location.set_location(scan_location)
                scan_locations.add_scan(lpa_location)
            except Exception as e:
                raise Exception(
                    f"Error downloading scanned document {lpa_location.template}: {e}"
                )

        # Download the continuation sheet scans, if they exist
        if not continuation_locations or len(continuation_locations) == 0:
            return scan_locations

        location_position = 0
        for continuation_location in continuation_locations:
            try:
                # Extract the file path and bucket name from the S3 URL
                path_parts = self.extract_s3_file_path(continuation_location.location)
                # Construct the local file path for the downloaded scan
                scan_location = f'{output_folder_path}/{path_parts["file_path"]}'
                logger.debug(
                    f"Attempting download from bucket: {path_parts['bucket']}, "
                    f"key: {path_parts['file_path']}, path: {scan_location}"
                )
                # Download the scan from S3 and save it to the local file path
                self.s3.download_file(
                    path_parts["bucket"], path_parts["file_path"], scan_location
                )
                # Add the local file path to the dictionary of downloaded scan locations
                location_position += 1

                continuation_location.set_location(scan_location)
                scan_locations.add_continuation(
                    key=f"continuation_{location_position}",
                    continuation=continuation_location,
                )

            except Exception as e:
                raise Exception(
                    f"Error downloading scanned continuation sheet {continuation_location.location}: {e}"
                )

        return scan_locations

    def put_images_to_bucket(
        self,
        path_selection: dict,
        uid: str,
        continuation_instruction_count: int,
        continuation_preference_count: int,
        continuation_unknown_count: int,
    ) -> list:
        """
        Puts the selected images in the specified S3 bucket.
        Raises an Exception if there is an error in adding any file to the bucket.
        Args:
        path_selection (dict): A dictionary containing the key-value pairs where the key is the image name
                                and the value is the path of the image file.
        Returns: list of images uploaded
        """
        images_uploaded = []
        for key, value in path_selection.items():
            image = f"iap-{uid}-{key}"
            try:
                self.s3.put_object(
                    Bucket=self.iap_bucket,
                    Key=image,
                    Body=open(value, "rb"),
                    ServerSideEncryption="AES256",
                    Metadata={
                        "ContinuationSheetsInstructions": str(
                            continuation_instruction_count
                        ),
                        "ContinuationSheetsPreferences": str(
                            continuation_preference_count
                        ),
                        "ContinuationSheetsUnknown": str(continuation_unknown_count),
                        "ProcessError": "0",
                    },
                )
                logger.debug(f"File '{image}' added to the '{self.iap_bucket}' bucket.")
                images_uploaded.append(image)
            except Exception as e:
                raise Exception(
                    f"Failed to add file '{image}' to the '{self.iap_bucket}' bucket: {e}"
                )

        return images_uploaded

    def put_error_image_to_bucket(self, uid) -> None:
        """
        Puts an error file in the specified S3 bucket.
        Raises an Exception if there is an error in adding the file to the bucket.
        """
        try:
            self.s3.put_object(
                Bucket=self.iap_bucket,
                Key=f"iap-{uid}-instructions",
                ServerSideEncryption="AES256",
                Metadata={
                    "ContinuationSheetsInstructions": "0",
                    "ContinuationSheetsPreferences": "0",
                    "ContinuationSheetsUnknown": "0",
                    "ProcessError": "1",
                },
            )
            logger.debug("Error file added to S3 bucket.")
        except Exception as e:
            raise Exception(f"Error: Failed to add error file to bucket. {e}")
