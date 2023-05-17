import datetime
import copy
import cv2
import re
from pyzbar.pyzbar import decode
from collections import Counter
from fuzzywuzzy import fuzz

from form_tools.form_operators import FormOperator
from form_tools.form_meta.form_meta import FormPage
from form_tools.utils.image_reader import ImageReader
from app.utility.custom_logging import custom_logger

logger = custom_logger("extraction_service")


class ExtractionService:
    def __init__(
        self, extraction_folder_path, folder_name, output_folder_path, info_msg
    ):
        self.extraction_folder_path = extraction_folder_path
        self.folder_name = folder_name
        self.output_folder_path = output_folder_path
        self.info_msg = info_msg

    def run_iap_extraction(self, scan_locations: dict) -> list:
        form_operator = FormOperator.create_from_config(
            f"{self.extraction_folder_path}/opg-config.yaml"
        )
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

    def get_matching_scan_item(
        self,
        scan_locations: dict,
        complete_meta_store: dict,
        form_meta_directory: str,
        form_operator: FormOperator,
    ) -> dict:
        """
        Find the matching scan item from a list of scan locations by attempting to match based on barcodes and OCR.
        Returns a dictionary containing the match and the scan location.
        """
        matched_lpa_scans_store = {"scan": {"match": {}, "scan_location": ""}}
        matches = []
        # Attempt to match based on barcodes
        for scan_location in scan_locations["scans"]:
            processed_images = self.get_preprocessed_images(
                scan_location, form_operator
            )
            logger.debug(f"Attempting to match {scan_location} based on barcodes...")
            matched_items = self.find_matches_from_barcodes(
                processed_images, complete_meta_store
            )
            logger.debug(
                f"Barcode matches for {scan_location}: {len(matched_items['image_page_map'])}"
            )
            if len(matched_items["image_page_map"]) > 0:
                matched_lpa_scans_store["scan"]["match"] = matched_items
                matched_lpa_scans_store["scan"]["scan_location"] = scan_location
                matched_lpa_scans_store_deep = copy.deepcopy(matched_lpa_scans_store)
                matches.append(matched_lpa_scans_store_deep)

        # Check if there is exactly one match
        logger.debug(f"Matched LPA scan documents based on barcodes: {len(matches)}")
        if len(matches) > 1:
            raise Exception(
                "More than one matching document path for LPA barcode scans"
            )
        elif len(matches) == 1:
            return matched_lpa_scans_store

        # Attempt to match based on OCR
        logger.debug("Attempting to match scans based on OCR...")
        for scan_location in scan_locations["scans"]:
            processed_images = self.get_preprocessed_images(
                scan_location, form_operator
            )
            matched_items = self.get_ocr_matches(
                processed_images, form_operator, form_meta_directory
            )
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

    def get_matching_continuation_items(
        self,
        scan_locations: dict,
        form_meta_directory: str,
        form_operator: FormOperator,
    ) -> dict:
        """
        This function attempts to match continuation scan locations with corresponding items using barcodes and OCR.

        :param scan_locations: Dictionary containing scan locations of the form.
        :param form_meta_directory: Directory containing the form meta data.
        :param form_operator: Operator for handling form data.
        :return: Dictionary containing matched continuation documents.
        """
        matched_lpa_scans_store = {}

        # Loop through scan locations and attempt to match them
        for key, scan_location in scan_locations["continuations"].items():
            # Get preprocessed images for current scan location
            processed_images = self.get_preprocessed_images(
                scan_location, form_operator
            )

            # Get form meta data
            matching_meta_store = form_operator.form_meta_store(form_meta_directory)

            logger.debug(f"Attempting to match {scan_location} based on barcodes...")
            # Attempt to match based on barcodes
            matched_items = self.find_matches_from_barcodes(
                processed_images, matching_meta_store
            )
            logger.debug(
                f"Barcode matches for {scan_location}: {len(matched_items['image_page_map'])}"
            )

            # If no matches found using barcodes, attempt to match using OCR
            if len(matched_items["image_page_map"]) == 0:
                logger.debug(f"Attempting to match {scan_location} based on OCR...")
                matched_items = self.get_ocr_matches(
                    processed_images, form_operator, form_meta_directory
                )

            # If matches found, store them in the matched LPA scans store
            if len(matched_items["image_page_map"]) > 0:
                if "continuation_" in key:
                    matched_lpa_scans_store[key] = {}
                    matched_lpa_scans_store[key]["match"] = matched_items
                    matched_lpa_scans_store[key]["scan_location"] = scan_location

        logger.debug(f"Matched continuation documents: {len(matched_lpa_scans_store)}")

        return matched_lpa_scans_store

    @staticmethod
    def extract_images(
        matched_items: dict,
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
            raise Exception(e)

    @staticmethod
    def get_preprocessed_images(form_path: str, form_operator: FormOperator) -> list:
        """
        Preprocesses the images of a form at the specified file path using the
        provided FormOperator object.

        Args:
            form_path (str): A string containing the file path of the form to be processed.
            form_operator (FormOperator): A FormOperator object used to preprocess the form images.

        Returns:
            list: A list of preprocessed form images after being auto-rotated based on text direction.
        """
        logger.debug(f"Reading form from path: {form_path}")
        _, imgs = ImageReader.read(form_path)

        logger.debug("Auto-rotating images based on text direction...")
        rotated_images = form_operator.auto_rotate_form_images(imgs)

        logger.debug(f"Total images found: {len(rotated_images)}")

        return rotated_images

    def get_ocr_matches(
        self,
        processed_images: list,
        form_operator: FormOperator,
        form_meta_directory: str,
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
        logger.debug("Further image processing...")
        form_images_doubled = self.double_image_size(processed_images)
        logger.debug("Applying OCR to extract text from images...")
        form_images_text = form_operator.form_images_to_text(form_images_doubled)
        logger.debug("Filtering metadata store by form regex...")
        # this is based on matching the form regex to filter down the number of matching metadata docs
        matching_meta_store = self.match_first_form_image_text_to_form_meta(
            form_meta_directory, form_images_text, form_operator
        )
        logger.debug(
            f"Created following metadata store based on form regex: {matching_meta_store}"
        )

        logger.debug("Attempting to identify matches based on text identification")
        matched_items = self.mixed_mode_page_identifier(
            form_images_text, matching_meta_store, processed_images
        )
        logger.debug(
            f"Total matched based on OCR: {len(matched_items['image_page_map'])}"
        )

        return matched_items

    def find_matches_from_barcodes(self, images: list, form_metastore: dict) -> dict:
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
        matched_meta = {"meta_id": "", "image_page_map": {}}

        # Iterate over each image and find its barcode
        for img in images:
            height, width = img.shape[:2]
            roi = img[0 : height // 3, 2 * width // 3 : width]
            barcodes = decode(roi)

            barcodes_decoded = []
            for barcode in barcodes:
                barcodes_decoded.append(barcode.data.decode("utf-8"))
                print(barcode.data.decode("utf-8"))

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
        form_meta_directory: str,
        form_images_as_strings: list,
        form_operator: FormOperator,
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
        self, form_images_as_strings: list, form_metastore: dict, form_images: list
    ) -> dict:
        scan_to_template_distances = self.create_scan_to_template_distances(
            form_images_as_strings, form_metastore
        )
        sorted_scan_template_entities = sorted(
            scan_to_template_distances,
            key=lambda x: (-x["distance"], x["template_page_no"], x["scan_page_no"]),
        )
        similarity_score = self.get_similarity_score(sorted_scan_template_entities)
        meta_id_to_use = self.get_meta_id_to_use(sorted_scan_template_entities)
        matching_image_results = self.get_matching_image_results(
            meta_id_to_use, similarity_score, sorted_scan_template_entities, form_images
        )
        return matching_image_results

    def create_scan_to_template_distances(self, form_images_as_strings, form_metastore):
        scan_to_template_similarities = []
        for meta_id, meta in form_metastore.items():
            for form_page in meta.form_pages:
                meta_page_text = self.get_meta_page_text(form_page)
                for scan_page_no, form_image_as_string in enumerate(
                    form_images_as_strings, start=1
                ):
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
            meta_page_text = file.read().replace("\n", "")
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
    ):
        matching_image_results = {"meta_id": meta_id_to_use, "image_page_map": {}}
        if similarity_score < 0.7:
            return matching_image_results
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
            matching_image_results["image_page_map"].setdefault(
                template_page_no, []
            ).append(form_images[scan_page_no - 1])
            msg = (
                f"Match on {meta_id_to_use} with OCR match for scan page number {scan_page_no} "
                f"from template page number {template_page_no}"
            )
            logger.debug(msg)
            self.info_msg.matched_templates.append(msg)
        return matching_image_results
