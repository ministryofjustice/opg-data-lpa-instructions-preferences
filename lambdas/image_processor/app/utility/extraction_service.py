import datetime
import copy
import os
import sys

import cv2
import re

import numpy as np
import pypdf
from pyzbar.pyzbar import decode
from collections import Counter
from fuzzywuzzy import fuzz

from form_tools.form_operators import FormOperator
from form_tools.form_meta.form_meta import FormPage
from form_tools.utils.image_reader import ImageReader
from app.utility.custom_logging import custom_logger
from app.utility.bucket_manager import ScanLocationStore
from typing import List
from PIL import UnidentifiedImageError
import tempfile

logger = custom_logger("extraction_service")

class FilteredMetastore:
    def __init__(self, filtered_metastore: dict, filtered_continuation_metastore: dict):
        self.filtered_metastore = filtered_metastore
        self.filtered_continuation_metastore = filtered_continuation_metastore


class MatchingMetaToImages:
    def __init__(self, meta_id: str = "", image_page_map: dict = None):
        if image_page_map is None:
            image_page_map = {}
        self.meta_id = meta_id
        self.image_page_map = image_page_map

    @property
    def size(self):
        return len(self.image_page_map)


class MatchingItem:
    def __init__(self, match: MatchingMetaToImages, scan_location: str):
        self.__match = match
        self.__scan_location = scan_location

    @property
    def match(self) -> MatchingMetaToImages:
        return self.__match

    @property
    def scan_location(self) -> str:
        return self.__scan_location


class MatchingItemsStore:
    def __init__(self):
        self.__matching_items = {}

    @property
    def matching_items(self) -> dict:
        return self.__matching_items

    def add_item(self, key: str, matching_item: MatchingItem) -> None:
        self.__matching_items[key] = matching_item

    def size(self) -> int:
        return len(self.__matching_items.items())


class ExtractionService:
    def __init__(
        self, extraction_folder_path, folder_name, output_folder_path, info_msg
    ):
        self.extraction_folder_path = extraction_folder_path
        self.folder_name = folder_name
        self.output_folder_path = output_folder_path
        self.info_msg = info_msg
        self.matched_continuations_from_scans = MatchingItemsStore()

    def run_iap_extraction(self, scan_locations: ScanLocationStore) -> list:
        form_operator = FormOperator.create_from_config(
            f"{self.extraction_folder_path}/opg-config.yaml"
        )
        continuation_keys_to_use = []
        run_timestamp = int(datetime.datetime.utcnow().timestamp())
        form_meta_directory = f"{self.extraction_folder_path}/metadata"
        complete_meta_store = form_operator.form_meta_store(form_meta_directory)

        # Find matches based on Scans (only one should match)
        scan_sheet_store = self.get_matching_scan_item(
            scan_locations, complete_meta_store, form_operator
        )

        # Find matches based on Continuation sheets (multiple matches possible)
        continuation_sheet_store = self.get_matching_continuation_items(
            scan_locations, complete_meta_store, form_operator
        )

        combined_continuation_sheet_store = self.combine_continuation_meta_stores(
            form_scan_continuation_store=self.matched_continuations_from_scans,
            continuation_sheet_store=continuation_sheet_store,
        )

        if scan_sheet_store.size() == 0:
            raise Exception("No matches found in any documents")

        complete_matching_store = self.combine_meta_stores(
            scan_sheet_store, combined_continuation_sheet_store
        )
        
        for (
            key,
            matched_document_store_item,
        ) in complete_matching_store.matching_items.items():
            pass_dir = f"{self.output_folder_path}/pass/{self.folder_name}/{key}"
            fail_dir = f"{self.output_folder_path}/fail/{self.folder_name}/{key}"
            matched_document_items = matched_document_store_item.match
            meta_id = matched_document_items.meta_id
            meta = complete_meta_store[meta_id]
            document_path = matched_document_store_item.scan_location
            self.extract_images(
                matched_document_items,
                meta,
                meta_id,
                form_operator,
                document_path,
                pass_dir,
                fail_dir,
                run_timestamp,
            )
            # If the key contains "continuation_", add it to the list of continuation keys to use
            if "continuation_" in key:
                continuation_keys_to_use.append(key)

        return continuation_keys_to_use

    @staticmethod
    def combine_meta_stores(
        store_a: MatchingItemsStore, store_b: MatchingItemsStore
    ) -> MatchingItemsStore:
        combined_store = MatchingItemsStore()
        for key, value in store_a.matching_items.items():
            combined_store.add_item(key, value)
        for key, value in store_b.matching_items.items():
            combined_store.add_item(key, value)
        return combined_store

    @staticmethod
    def combine_continuation_meta_stores(
        form_scan_continuation_store: MatchingItemsStore,
        continuation_sheet_store: MatchingItemsStore,
    ) -> MatchingItemsStore:
        combined_continuation_store = MatchingItemsStore()
        continuation_count = 1
        for _, value in form_scan_continuation_store.matching_items.items():
            combined_continuation_store.add_item(
                f"continuation_{continuation_count}", value
            )
            continuation_count += 1

        for _, value in continuation_sheet_store.matching_items.items():
            combined_continuation_store.add_item(
                f"continuation_{continuation_count}", value
            )
            continuation_count += 1

        return combined_continuation_store

    @staticmethod
    def filter_metastore_based_on_template(
        complete_meta_store: dict, template: str
    ) -> FilteredMetastore:
        metastore_mapping = {
            "LPA117": {"templates": ["pfa117"], "continuation_templates": ["pfa_c"]},
            "LPA114": {"templates": ["hw114"], "continuation_templates": ["pfa_c"]},
            "LP1H": {
                "templates": ["lp1h"],
                "continuation_templates": ["lpc_as_part_of_scan"],
            },
            "LP1F": {
                "templates": ["lp1f"],
                "continuation_templates": ["lpc_as_part_of_scan"],
            },
            "LPC": {
                "templates": ["lpc", "lpc_lp", "pfa_c"],
                "continuation_templates": [],
            },
        }
        filtered_metastore = {}
        filtered_continuation_metastore = {}
        try:
            matched_metas = metastore_mapping[template]
            for matched_meta in matched_metas["templates"]:
                filtered_metastore[matched_meta] = complete_meta_store[matched_meta]
            for matched_continuation_meta in matched_metas["continuation_templates"]:
                filtered_continuation_metastore[
                    matched_continuation_meta
                ] = complete_meta_store[matched_continuation_meta]
            return FilteredMetastore(
                filtered_metastore=filtered_metastore,
                filtered_continuation_metastore=filtered_continuation_metastore,
            )
        except KeyError:
            return FilteredMetastore(
                filtered_metastore=complete_meta_store,
                filtered_continuation_metastore={},
            )

    @staticmethod
    def is_pdf_file(file_path):
        try:
            with open(file_path, "rb") as file:
                pdf = pypdf.PdfReader(file)
                return len(pdf.pages) > 0
        except pypdf.errors.PdfReadError:
            return False

    def get_matching_scan_item(
        self,
        scan_locations: ScanLocationStore,
        complete_meta_store: dict,
        form_operator: FormOperator,
    ) -> MatchingItemsStore:
        """
        Find the matching scan item from a list of scan locations by attempting to match based on barcodes and OCR.
        Returns a dictionary containing the match and the scan location.
        """
        matches = []
        # Attempt to match based on barcodes
        for scan_location in scan_locations.scans:
            if not self.is_pdf_file(scan_location.location):
                continue

            filtered_metastore = self.filter_metastore_based_on_template(
                complete_meta_store, scan_location.template
            )

            processed_images = self.get_preprocessed_images(
                scan_location.location, form_operator
            )

            if processed_images == None:
                continue

            logger.debug(
                f"Attempting to match {scan_location.template} - {scan_location.location} based on barcodes..."
            )
            matched_items = self.find_matches_from_barcodes(
                processed_images, filtered_metastore, scan_location.location
            )

            logger.debug(
                f"Barcode matches for {scan_location.location}: {len(matched_items.image_page_map)}"
            )
            if len(matched_items.image_page_map) > 0:
                matching_item = MatchingItem(matched_items, scan_location.location)
                matched_lpa_scans_store = MatchingItemsStore()
                matched_lpa_scans_store.add_item("scan", matching_item)
                matched_lpa_scans_store_deep = copy.deepcopy(matched_lpa_scans_store)
                matches.append(matched_lpa_scans_store_deep)
                break

        # Check if there is exactly one match
        logger.debug(f"Matched LPA scan documents based on barcodes: {len(matches)}")
        if len(matches) > 1:
            # should not be possible with current logic
            raise Exception(
                "More than one matching document path for LPA barcode scans"
            )
        elif len(matches) == 1:
            return matches[0]

        # Attempt to match based on OCR
        matches = []
        logger.debug("Attempting to match scans based on OCR...")
        for scan_location in scan_locations.scans:
            filtered_metastore = self.filter_metastore_based_on_template(
                complete_meta_store, scan_location.template
            )
            processed_images = self.get_preprocessed_images(
                scan_location.location, form_operator
            )
            if processed_images == None:
                continue
            matched_items = self.get_ocr_matches(
                processed_images,
                form_operator,
                filtered_metastore,
                scan_location.location,
            )

            if len(matched_items.image_page_map) > 0:
                matching_item = MatchingItem(matched_items, scan_location.location)
                matched_lpa_scans_store = MatchingItemsStore()
                matched_lpa_scans_store.add_item("scan", matching_item)
                matched_lpa_scans_store_deep = copy.deepcopy(matched_lpa_scans_store)
                matches.append(matched_lpa_scans_store_deep)
                break

        # Check if there is exactly one match
        logger.debug(f"Matched LPA scan documents based on OCR: {len(matches)}")
        if len(matches) > 1:
            # should not be possible with current logic
            raise Exception("More than one matching document path for LPA OCR scans")
        elif len(matches) == 1:
            return matches[0]

        return MatchingItemsStore()

    def get_matching_continuation_items(
        self,
        scan_locations: ScanLocationStore,
        complete_meta_store: dict,
        form_operator: FormOperator,
    ) -> MatchingItemsStore:
        """
        This function attempts to match continuation scan locations with corresponding items using barcodes and OCR.

        :param scan_locations: Dictionary containing scan locations of the form.
        :param complete_meta_store: Complete store of the form meta data.
        :param form_operator: Operator for handling form data.
        :return: Dictionary containing matched continuation documents.
        """
        matched_lpa_scans_store = MatchingItemsStore()
        # Loop through scan locations and attempt to match them
        for key, scan_location in scan_locations.continuations.items():
            if not self.is_pdf_file(scan_location.location):
                continue
            filtered_metastore = self.filter_metastore_based_on_template(
                complete_meta_store, scan_location.template
            )
            # Get preprocessed images for current scan location
            processed_images = self.get_preprocessed_images(
                scan_location.location, form_operator
            )
            if processed_images == None:
                continue
            logger.debug(
                f"Attempting to match {scan_location.location} based on barcodes..."
            )
            # Attempt to match based on barcodes
            matched_items = self.find_matches_from_barcodes(
                processed_images, filtered_metastore, scan_location.location
            )

            logger.debug(
                f"Barcode matches for {scan_location.location}: {len(matched_items.image_page_map)}"
            )

            # If no matches found using barcodes, attempt to match using OCR
            if len(matched_items.image_page_map) == 0:
                logger.debug(
                    f"Attempting to match {scan_location.location} based on OCR..."
                )
                matched_items = self.get_ocr_matches(
                    processed_images,
                    form_operator,
                    filtered_metastore,
                    scan_location.location,
                )

            # If matches found, store them in the matched LPA scans store
            if len(matched_items.image_page_map) > 0:
                if "continuation_" in key:
                    matching_item = MatchingItem(matched_items, scan_location.location)
                    matched_lpa_scans_store.add_item(key, matching_item)

        logger.debug(
            f"Matched continuation documents: {matched_lpa_scans_store.size()}"
        )

        return matched_lpa_scans_store

    @staticmethod
    def extract_images(
        matched_items: MatchingMetaToImages,
        meta: dict,
        meta_id: str,
        form_operator: FormOperator,
        scan_path: str,
        pass_dir: str,
        fail_dir: str,
        run_timestamp: int,
    ) -> None:
        """
        Extracts images and fields from a form, aligns them to a metadata template, and saves the result
        in the pass directory. If there is an error, saves a copy in the fail directory.

        Parameters:
            matched_items (MatchingMetaToImages): A dictionary with information about the matched items.
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
                matched_items.image_page_map, form_meta=meta, debug=False
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
            raise Exception(e)

    def get_preprocessed_images(
        self, form_path: str, form_operator: FormOperator
    ) -> list:
        """
        Preprocesses the images of a form at the specified file path using the
        provided FormOperator object.

        Args:
            form_path (str): A string containing the file path of the form to be processed.
            form_operator (FormOperator): A FormOperator object used to preprocess the form images.
            metastore (dict): store of meta templates

        Returns:
            list: A list of preprocessed form images after being auto-rotated based on text direction.
        """
        logger.debug(f"Reading form from path: {form_path}")
        try:
            with tempfile.TemporaryDirectory() as path:
                _, imgs = ImageReader.read(form_path, conversion_parameters={"output_folder": path})

                logger.debug("Auto-rotating images based on text direction...")
                rotated_images = form_operator.auto_rotate_form_images(imgs)

        except UnidentifiedImageError:
            logger.debug(f"Unable to match {form_path}")
            pass

        logger.debug(f"Total images found: {len(rotated_images)}")

        return None

    @staticmethod
    def smart_threshold_images(image_list):
        # Create an empty list to store the new images
        thresholded_images = []

        # Loop through each image in the input list
        for image in image_list:
            # Get the current size of the image
            # Convert the image to grayscale
            grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            average_intensity = np.mean(grayscale)
            # Apply the threshold using the average intensity
            _, thresholded = cv2.threshold(
                grayscale, average_intensity - 50, 255, cv2.THRESH_BINARY
            )

            thresholded_images.append(thresholded)

        # Return the list of doubled-size images
        return thresholded_images

    @staticmethod
    def mask_images(metastore, images):
        updated_images = []
        for image in images:
            for meta_id, meta in metastore.items():
                form_meta_loc = meta.form_template
                template_files = os.listdir(form_meta_loc)
                template = cv2.imread(os.path.join(form_meta_loc, template_files[0]))

                # Get the height and width of the template image
                template_height, template_width, _ = template.shape

                # Resize the input image to match the template size
                resized_image = cv2.resize(image, (template_width, template_height))

                form_fields = meta.form_fields
                average_color = np.mean(image, axis=(0, 1))
                for field in form_fields:
                    field_bb = field.bounding_box
                    top_left = (field_bb.left, field_bb.top)
                    bottom_right = (field_bb.right, field_bb.bottom)

                    cv2.rectangle(
                        resized_image,
                        top_left,
                        bottom_right,
                        average_color,
                        thickness=cv2.FILLED,
                    )

            updated_images.append(resized_image)

        return updated_images

    def get_ocr_matches(
        self,
        processed_images: list,
        form_operator: FormOperator,
        metastore: FilteredMetastore,
        scan_location: str,
    ) -> MatchingMetaToImages:
        """
        Applies OCR to extract text from images, filters metadata by matching form regex,
        and attempts to identify matches based on text identification.

        Args:
            - processed_images (List[Any]): A list of processed images to extract text from.
            - form_operator (Any): A form operator object with `form_images_to_text` method.
            - metastore (dict): A directory containing form metadata documents.

        Returns:
            - matched_items (Dict[str, Any]): A dictionary containing the results of the matching process.
              The dictionary contains keys:
              - 'image_page_map' (Dict[Tuple[int, int], List[int]]): A dictionary mapping a tuple of
                (form_index, image_index) to a list of matched page indices in metadata documents.
              - 'match_confidences' (List[float]): A list of match confidences for all matched items.
        """
        # If we have narrowed it down to 1 meta then we can safely mask away
        # where we would find the contents of the file to make matches more accurate
        scan_and_continuation_matches = []
        # ====== Process scan documents ======
        if len(metastore.filtered_metastore) == 1:
            logger.debug("Further image processing based on scan template...")
            masked_images = self.mask_images(
                metastore.filtered_metastore, processed_images
            )
            ocr_refined_images = self.smart_threshold_images(masked_images)
        else:
            ocr_refined_images = processed_images

        logger.debug("Applying OCR to extract text from images...")
        form_images_text = form_operator.form_images_to_text(ocr_refined_images)

        logger.debug("Attempting to identify matches based on text identification")
        matched_items = self.mixed_mode_page_identifier(
            form_images_as_strings=form_images_text,
            form_metastore=metastore.filtered_metastore,
            form_images=processed_images,
            inline_continuation=False,
        )
        # We are only interested in first element for this one
        matched_item = matched_items[0]

        if matched_item.size > 0:
            scan_and_continuation_matches.append(matched_item)

        logger.debug(
            f"Total matched based on OCR: {len(scan_and_continuation_matches)}"
        )

        if len(scan_and_continuation_matches) == 0:
            return MatchingMetaToImages()

        if len(metastore.filtered_continuation_metastore) == 0:
            return scan_and_continuation_matches[0]

        # ====== Process continuation sheets ======
        if len(metastore.filtered_continuation_metastore) == 1:
            logger.debug("Further image processing based on continuation template...")
            masked_images = self.mask_images(
                metastore.filtered_continuation_metastore, processed_images
            )
            ocr_refined_images = self.smart_threshold_images(masked_images)
        else:
            ocr_refined_images = processed_images

        logger.debug(
            "Applying OCR to extract continuation text from images where it exists..."
        )
        form_images_text = form_operator.form_images_to_text(ocr_refined_images)

        logger.debug("Attempting to identify matches based on text identification")
        matched_items = self.mixed_mode_page_identifier(
            form_images_as_strings=form_images_text,
            form_metastore=metastore.filtered_continuation_metastore,
            form_images=processed_images,
            inline_continuation=True,
        )
        logger.debug(f"Total continuation matched based on OCR: {len(matched_items)}")

        scan_and_continuation_matches.extend(matched_items)

        matched_meta_ids = self.get_meta_matched_meta_ids(scan_and_continuation_matches)

        if len(scan_and_continuation_matches) > 1:
            if self.match_combination_conditions_correct(matched_meta_ids):
                logger.debug("Additional matches based on inline continuation sheets")
                matched_image = self.split_out_scans_from_continuation_matches(
                    scan_and_continuation_matches, scan_location
                )
                return matched_image

        return scan_and_continuation_matches[0]

    @staticmethod
    def match_combination_conditions_correct(matched_meta_ids):
        count_lp1f = matched_meta_ids.count("lp1f")
        count_lp1h = matched_meta_ids.count("lp1h")

        if count_lp1f > 1 or count_lp1h > 1:
            return False

        if count_lp1f > 0 and count_lp1h > 0:
            return False

        return True

    def split_out_scans_from_continuation_matches(
        self, matching_images: List[MatchingMetaToImages], scan_location: str
    ):
        matched_scan = None
        matched_continuations = []
        for matching_image in matching_images:
            if matching_image.meta_id in ["lp1f", "lp1h", "pfa117", "hw114"]:
                matched_scan = matching_image
            elif matching_image.meta_id in ["lpc_as_part_of_scan", "pfa_c"]:
                matched_continuations.append(matching_image)

        for count, matched_continuation in enumerate(matched_continuations):
            scan_continuation_item = MatchingItem(
                match=matched_continuation, scan_location=scan_location
            )
            self.matched_continuations_from_scans.add_item(
                f"continuation_{count}", scan_continuation_item
            )

        return matched_scan

    @staticmethod
    def get_barcodes_scan_number_mapping(images):
        """
        Attempt to find barcodes in top right of each image
        and add them to a dict containing scan number and the decoded barcode in utf8.
        """
        image_barcode_dict = {}
        # Iterate over each image and find its barcode
        for image_count, image in enumerate(images):
            height, width = image.shape[:2]
            roi = image[0 : height // 3, 2 * width // 3 : width]
            barcodes = decode(roi)

            barcodes_decoded = []
            for barcode in barcodes:
                barcodes_decoded.append(barcode.data.decode("utf-8"))

            if len(barcodes_decoded) > 0:
                image_barcode_dict[image_count] = barcodes_decoded[0]

        return image_barcode_dict

    @staticmethod
    def get_meta_matched_meta_ids(
        matching_meta_to_images_list: List[MatchingMetaToImages],
    ):
        matched_meta_ids = []
        for matching_meta_to_images in matching_meta_to_images_list:
            matched_meta_ids.append(matching_meta_to_images.meta_id)
        return matched_meta_ids

    def find_matches_from_barcodes(
        self, images: list, form_metastore: FilteredMetastore, scan_location: str
    ) -> MatchingMetaToImages:
        """
        Finds and matches barcodes in the input images to the corresponding template pages in the
        form metastore.

        Args:
            images (List[np.ndarray]): A list of images to be matched with templates.
            form_metastore (Dict[str, Any]): A dictionary containing form template metadata.
            scan_location (str): used for updating the location of continuation sheets that are part of the main scan

        Returns:
            Union[Dict[str, Any], List[Dict[str, Any]]]: If a match is found, a dictionary containing
            the metadata of the form template and a mapping between template pages and images. If no
            matches are found, an empty dictionary is returned. If too many matches are found, a
            dictionary with an empty image-page map is returned. If multiple matches are found, a list
            of dictionaries with the metadata and image-page mappings for each matched template is
            returned.
        """
        matching_meta_images = MatchingMetaToImages()
        image_barcode_dict = self.get_barcodes_scan_number_mapping(images)

        # Iterate over each form in the form_metastore and try to match it to an image by its barcode
        # ======= Pull out the scan matches  ======
        matching_images = []
        for meta_id, meta in form_metastore.filtered_metastore.items():
            matching_image_page = {}
            images_used = []
            form_pages_used = []

            for form_page in meta.form_pages:
                template_barcode = form_page.additional_args["extra"]["barcode"]

                for img_count, image_barcode in image_barcode_dict.items():
                    if template_barcode == image_barcode:
                        # Check that we haven't already matched this image or form page
                        if (
                            img_count not in images_used
                            and form_page.page_number not in form_pages_used
                        ):
                            logger.debug(
                                f"Barcode match on {template_barcode} for image {img_count} from page: {form_page.page_number}"
                            )
                            matching_image_page[form_page.page_number] = [
                                images[img_count]
                            ]
                            images_used.append(img_count)
                            form_pages_used.append(form_page.page_number)
                            self.info_msg.matched_templates.append(
                                f"Match on {meta_id} with barcode {template_barcode} "
                                f"for scan page number {img_count} from template page {form_page.page_number}"
                            )

            matching_meta_images.meta_id = meta_id
            matching_meta_images.image_page_map = matching_image_page

            if len(matching_meta_images.image_page_map) > 0:
                matched_meta_deep = copy.deepcopy(matching_meta_images)
                matching_images.append(matched_meta_deep)

        for matching_image in matching_images:
            if matching_image.meta_id in ["lpc", "lpc_lp", "pfa_c"]:
                return matching_images[0]

        # ======= Pull out the continuation matches for in-scan continuations ======
        for (
            continuation_meta_id,
            continuation_meta,
        ) in form_metastore.filtered_continuation_metastore.items():
            matching_image_page = {}
            images_used = []
            form_pages_used = []

            for form_page in continuation_meta.form_pages:
                template_barcode = form_page.additional_args["extra"]["barcode"]

                for img_count, image_barcode in image_barcode_dict.items():
                    if template_barcode == image_barcode:
                        # Check that we haven't already matched this image or form page
                        if img_count not in images_used:
                            logger.debug(
                                f"Barcode match on {template_barcode} for image {img_count} from page: {form_page.page_number}"
                            )
                            matching_image_page[form_page.page_number] = [
                                images[img_count]
                            ]
                            images_used.append(img_count)

                            form_pages_used.append(form_page.page_number)
                            self.info_msg.matched_templates.append(
                                f"Match on {continuation_meta_id} with barcode {template_barcode} "
                                f"for scan page number {img_count} from template page {form_page.page_number}"
                            )
                            matching_meta_images.meta_id = continuation_meta_id
                            matching_meta_images.image_page_map = matching_image_page
                            if len(matching_meta_images.image_page_map) > 0:
                                matched_meta_deep = copy.deepcopy(matching_meta_images)
                                matching_images.append(matched_meta_deep)

        # Handle the cases where we have too many or too few matches
        if len(matching_images) > 1:
            logger.debug("more than one match on Barcodes")

            matched_meta_ids = []
            for image in matching_images:
                matched_meta_ids.append(image.meta_id)

            if self.match_combination_conditions_correct(matched_meta_ids):
                logger.debug("Additional matches based on inline continuation sheets")
                matched_image = self.split_out_scans_from_continuation_matches(
                    matching_images, scan_location
                )
                return matched_image

            matching_meta_images.image_page_map = {}
            return matching_meta_images

        if len(matching_images) == 0:
            logger.debug("No matches on barcodes")
            return matching_meta_images

        # If we have exactly one match, return it
        return matching_images[0]

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
            image = cv2.resize(
                image,
                (round(2 * width), round(2 * height)),
                interpolation=cv2.INTER_LANCZOS4,
            )
            doubled_images.append(image)

        # Return the list of doubled-size images
        return doubled_images

    @staticmethod
    def match_first_form_image_text_to_form_meta(
        metastore: dict,
        form_images_as_strings: list,
        form_operator: FormOperator,
    ) -> dict:
        """Filters form meta directory using given form image string
        of first page

        Loops through `FormMetadata` objects in a given directory
        and only returns those where the given form images
        contains the given metadata's identifier

        Params:
            metastore (dict):
                The metastore of all our config items
            form_images_as_strings (List[str]):
                List of recognised text from a set of form images

        Return:
            (Dict[str, FormMetadata]):
                A dictionary of `FormMetadata` objects
        """
        results = {}
        for id, meta in metastore.items():
            valid, _ = form_operator.form_identifier_match(
                [form_images_as_strings[0]], meta
            )
            if valid:
                results[id] = meta
        return results

    @staticmethod
    def similarity_score(str1: str, str2: str) -> float:
        """
        Computes the similarity score between two strings by counting the number of common words
        and the number of unique words in each string separately.

        Args:
        - str1: A string representing the first input string
        - str2: A string representing the second input string

        Returns:
        A float value representing the similarity score between the two strings. The value
        ranges from 0.0 (no similarity) to 1.0 (exact match).
        """
        # remove non-alphanumeric characters and split into words
        words1 = re.findall(r"\w+", str1.lower())
        words2 = re.findall(r"\w+", str2.lower())

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

    def mixed_mode_page_identifier(
        self,
        form_images_as_strings: list,
        form_metastore: dict,
        form_images: list,
        inline_continuation: bool = False,
    ) -> List[MatchingMetaToImages]:
        scan_to_template_distances = self.create_scan_to_template_distances(
            form_images_as_strings, form_metastore
        )
        sorted_scan_template_entities = sorted(
            scan_to_template_distances,
            key=lambda x: (-x["distance"], x["scan_page_no"], x["template_page_no"]),
        )

        similarity_score = self.get_similarity_score(sorted_scan_template_entities)
        meta_id_to_use = self.get_meta_id_to_use(sorted_scan_template_entities)
        if not inline_continuation:
            matching_image_results_list = []
            matching_image_results = self.get_matching_image_results(
                meta_id_to_use,
                similarity_score,
                sorted_scan_template_entities,
                form_images,
            )
            matching_image_results_list.append(matching_image_results)
        else:
            matching_image_results_list = self.get_matching_continuation_image_results(
                meta_id_to_use,
                similarity_score,
                sorted_scan_template_entities,
                form_images,
            )

        return matching_image_results_list

    def create_scan_to_template_distances(self, form_images_as_strings, form_metastore):
        scan_to_template_similarities = []
        for meta_id, meta in form_metastore.items():
            for form_page in meta.form_pages:
                meta_page_text = self.get_meta_page_text(form_page)
                for scan_page_no, form_image_as_string in enumerate(
                    form_images_as_strings, start=1
                ):
                    # if meta_id == "lpa_pw":
                    distance = self.calculate_similarity_ratio(
                        form_page, form_image_as_string, meta_page_text
                    )
                    scan_info = {
                        "meta": meta_id,
                        "distance": distance,
                        "scan_page_no": scan_page_no,
                        "template_page_no": form_page.page_number,
                        "form_image_as_string": form_image_as_string,
                        "meta_page_text": meta_page_text,
                    }
                    scan_to_template_similarities.append(scan_info)
        return scan_to_template_similarities

    def get_meta_page_text(self, form_page):
        template_page_text_file = f"{self.extraction_folder_path}/target_texts/{form_page.additional_args['extra']['page_text']}"
        with open(template_page_text_file, "r") as file:
            meta_page_text = file.read()
        return meta_page_text

    @staticmethod
    def calculate_similarity_ratio(
        form_page: FormPage, form_image_as_string: str, meta_page_text: str
    ) -> float:
        """
        Calculates the similarity between the given `form_image_as_string`
        and `meta_page_text`, based on the `form_page.identifier` regex match.

        Args:
        - form_page (FormPage): An object representing the form page.
        - form_image_as_string (str): A string representation of the form image.
        - meta_page_text (str): A string representation of the meta page text.

        Returns:
        - ratio (float): The similarity ratio using Levenstein distance between `form_image_as_string` and
          `meta_page_text` if a regex match is found. Otherwise, returns 0.
        """
        page_regex = form_page.identifier
        regex_match = (
            True if re.search(page_regex, form_image_as_string, re.DOTALL) else False
        )

        if regex_match:
            ratio = fuzz.ratio(form_image_as_string, meta_page_text)
        else:
            ratio = 0

        return ratio

    def get_similarity_score(self, sorted_scan_template_entities):
        similarity_score = self.similarity_score(
            sorted_scan_template_entities[0]["meta_page_text"],
            sorted_scan_template_entities[0]["form_image_as_string"],
        )

        logger.debug(f"Top similarity score is: {similarity_score}")
        return similarity_score

    @staticmethod
    def get_meta_id_to_use(sorted_scan_template_entities):
        meta_id_to_use = sorted_scan_template_entities[0]["meta"]
        return meta_id_to_use

    def get_matching_image_results(
        self,
        meta_id_to_use,
        similarity_score,
        sorted_scan_template_entities,
        form_images,
    ) -> MatchingMetaToImages:
        matching_meta_images = MatchingMetaToImages()
        matching_meta_images.meta_id = meta_id_to_use
        if similarity_score < 0.7:
            return matching_meta_images
        template_pages_used = set()
        scan_pages_used = set()
        templates_to_keep = []
        for scan_template_entity in sorted_scan_template_entities:
            template_page_no = scan_template_entity["template_page_no"]
            scan_page_no = scan_template_entity["scan_page_no"]
            meta_id = scan_template_entity["meta"]
            if (
                template_page_no not in template_pages_used
                and scan_page_no not in scan_pages_used
                and meta_id == meta_id_to_use
            ):
                scan_pages_used.add(scan_page_no)
                template_pages_used.add(template_page_no)
                templates_to_keep.append(scan_template_entity)

        for template_to_keep in templates_to_keep:
            template_page_no = template_to_keep["template_page_no"]
            scan_page_no = template_to_keep["scan_page_no"]
            matching_meta_images.image_page_map.setdefault(template_page_no, []).append(
                form_images[scan_page_no - 1]
            )
            msg = (
                f"Match on {meta_id_to_use} with OCR match for scan page number {scan_page_no} "
                f"from template page number {template_page_no}"
            )
            logger.debug(msg)
            self.info_msg.matched_templates.append(msg)
        return matching_meta_images

    def get_matching_continuation_image_results(
        self,
        meta_id_to_use,
        similarity_score,
        sorted_scan_template_entities,
        form_images,
    ) -> List[MatchingMetaToImages]:
        matching_meta_images = MatchingMetaToImages()
        matching_meta_images.meta_id = meta_id_to_use
        if similarity_score < 0.7:
            return []
        scan_pages_used = set()
        templates_to_keep = []
        for scan_template_entity in sorted_scan_template_entities:
            scan_page_no = scan_template_entity["scan_page_no"]
            meta_id = scan_template_entity["meta"]
            distance = scan_template_entity["distance"]
            if (
                scan_page_no not in scan_pages_used
                and meta_id == meta_id_to_use
                and distance > 70
            ):
                scan_pages_used.add(scan_page_no)
                templates_to_keep.append(scan_template_entity)

        sorted_templates_to_keep = sorted(
            templates_to_keep,
            key=lambda x: (x["scan_page_no"], x["template_page_no"]),
        )

        matching_meta_images_list = []
        for template_to_keep in sorted_templates_to_keep:
            template_page_no = template_to_keep["template_page_no"]
            scan_page_no = template_to_keep["scan_page_no"]
            matching_meta_images = MatchingMetaToImages()
            matching_meta_images.meta_id = meta_id_to_use
            matching_meta_images.image_page_map.setdefault(template_page_no, []).append(
                form_images[scan_page_no - 1]
            )
            matching_meta_images_deep = copy.deepcopy(matching_meta_images)
            matching_meta_images_list.append(matching_meta_images_deep)
            msg = (
                f"Match on {meta_id_to_use} with OCR match for scan page number {scan_page_no} "
                f"from template page number {template_page_no}"
            )
            logger.debug(msg)
            self.info_msg.matched_templates.append(msg)

        return matching_meta_images_list
