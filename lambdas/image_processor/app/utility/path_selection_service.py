import cv2
import numpy as np

from app.utility.custom_logging import custom_logger

logger = custom_logger("path_selection_service")


class PathSelectionService:
    def __init__(self, folder_name):
        self.folder_name = folder_name

    @staticmethod
    def get_continuation_sheet_type(instructions, preferences):
        if preferences and instructions:
            return "BOTH"
        elif instructions:
            return "INSTRUCTIONS"
        elif preferences:
            return "PREFERENCES"
        else:
            return "NEITHER"

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
        instructions_and_preferences = self.find_instruction_and_preference_paths(
            path_selection, paths
        )
        logger.debug(
            f"List of IaP paths found: {instructions_and_preferences['path_selection']}"
        )

        # Extract the path selection and continuation sheet type from the instructions_and_preferences
        path_selection = instructions_and_preferences["path_selection"]
        continuation_sheet_type = self.get_continuation_sheet_type(
            instructions_and_preferences["continuation_instructions"],
            instructions_and_preferences["continuation_preferences"],
        )

        logger.debug(f"Continuation keys to use: {continuation_keys_to_use}")
        # Loop through each continuation key and get the corresponding continuation sheet paths
        continuation_sheets = {}
        for continuation_key in continuation_keys_to_use:
            path_filter = f"pass/{self.folder_name}/{continuation_key}"
            continuation_sheets[continuation_key] = self.get_continuation_sheet_paths(
                paths, continuation_sheet_type, path_filter
            )
        logger.debug(f"List of Continuation sheets found: {continuation_sheets}")
        logger.debug(f"Continuation sheet type: {continuation_sheet_type}")

        if not self.check_continuation_sheets_match_expected(
            continuation_sheets, continuation_sheet_type
        ):
            logger.warning(
                "Images extracted from Continuation Sheets do not match what is expected based on the checkbox"
            )
        # The following line can be uncommented once UML-3201 and UML-3202 are done. For now we only log not error
        # raise Exception("Images extracted from Continuation Sheets do not match what is expected based on the checkbox")

        # Created the final combined object of instructions, preferences and continuation sheets
        path_selection = self.merge_continuation_images_into_path_selection(
            path_selection, continuation_sheets
        )

        return path_selection

    @staticmethod
    def check_continuation_sheets_match_expected(
        continuation_sheets, continuation_sheet_type
    ):
        logger.debug("check_continuation_sheets_match_expected called")
        preferences_present = False
        instructions_present = False
        for (
            _,
            continuation_sheet_values,
        ) in continuation_sheets.items():
            for (
                _,
                continuation_page_value,
            ) in continuation_sheet_values.items():
                try:
                    continuation_page_type = continuation_page_value["type"]
                    logger.debug(f"continuation page type is {continuation_page_type}")
                    if continuation_page_type == "preferences":
                        preferences_present = True
                    if continuation_page_type == "instructions":
                        instructions_present = True
                except KeyError:
                    continue

        logger.debug("checking what we found against what we EXPECTED")
        if (
            continuation_sheet_type in ["PREFERENCES", "BOTH"]
            and not preferences_present
        ):
            return False

        if (
            continuation_sheet_type in ["INSTRUCTIONS", "BOTH"]
            and not instructions_present
        ):
            return False

        return True

    def find_instruction_and_preference_paths(
        self, path_selection: dict, paths: list
    ) -> dict:
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
                mandatory_fragments=["field_name=preferences"],
                one_of_fragments=[
                    "meta=lp1f",
                    "meta=lp1h",
                    "meta=pfa117",
                    "meta=hw114",
                    "meta=lpa_pw",
                    "meta=lpa_pa",
                    "meta=lp1f_lp",
                    "meta=lp1h_lp",
                ],
            ):
                path_selection["preferences"] = path
                logger.debug(f"Found preferences path {path}")
            elif self.string_fragments_in_string(
                target_string=path,
                mandatory_fragments=["field_name=instructions"],
                one_of_fragments=[
                    "meta=lp1f",
                    "meta=lp1h",
                    "meta=pfa117",
                    "meta=hw114",
                    "meta=lpa_pw",
                    "meta=lpa_pa",
                    "meta=lp1f_lp",
                    "meta=lp1h_lp",
                ],
            ):
                path_selection["instructions"] = path
                logger.debug(f"Found instructions path {path}")
            elif self.string_fragments_in_string(
                target_string=path,
                mandatory_fragments=[
                    "field_name=continuation_checkbox_instructions",
                ],
                one_of_fragments=[
                    "meta=lp1f",
                    "meta=lp1h",
                    "meta=lp1f_lp",
                    "meta=lp1h_lp",
                ],
            ):
                if self.detect_marked_checkbox(path):
                    continuation_instructions = True
            elif self.string_fragments_in_string(
                target_string=path,
                mandatory_fragments=[
                    "field_name=continuation_checkbox_preferences",
                ],
                one_of_fragments=[
                    "meta=lp1f",
                    "meta=lp1h",
                    "meta=lp1f_lp",
                    "meta=lp1h_lp",
                ],
            ):
                if self.detect_marked_checkbox(path):
                    continuation_preferences = True

        return {
            "path_selection": path_selection,
            "continuation_instructions": continuation_instructions,
            "continuation_preferences": continuation_preferences,
        }

    def get_continuation_sheet_paths(
        self, paths, continuation_sheet_type, path_filter
    ) -> dict:
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
        pages = {"p1": {"path": "", "type": ""}, "p2": {"path": "", "type": ""}}

        checkboxes = {
            "preferences": {
                "p1": "field_name=preferences_checkbox_p1",
                "p2": "field_name=preferences_checkbox_p2",
            },
            "instructions": {
                "p1": "field_name=instructions_checkbox_p1",
                "p2": "field_name=instructions_checkbox_p2",
            },
        }
        checked_checkboxes = {"p1": [], "p2": []}
        warning_message = "Found unexpected continuation sheet type."

        # Loops over the paths filtered by our filter.
        # Finds out which checkbox type is ticked for each page.
        # Adds the path for the actual text box for each page
        for path in paths:
            if path_filter in path:
                for page in ["p1", "p2"]:
                    for sheet_type in ["preferences", "instructions"]:
                        checkbox = checkboxes[sheet_type][page]
                        # Checks on checkbox type for each page and appends and checked boxes to a list
                        if self.string_fragments_in_string(
                            target_string=path,
                            mandatory_fragments=[checkbox],
                            one_of_fragments=["meta=lpc", "meta=lpc_lp"],
                        ):
                            if self.detect_marked_checkbox(path):
                                if continuation_sheet_type in [
                                    "BOTH",
                                    sheet_type.upper(),
                                ]:
                                    checked_checkboxes[page].append(sheet_type)
                                else:
                                    logger.warning(
                                        f"{warning_message} Expected: {continuation_sheet_type}, Actual: {sheet_type}"
                                    )
                                    checked_checkboxes[page].append(sheet_type)
                        # Appends the continuation sheet text to path item of pages dict for each page
                        elif self.string_fragments_in_string(
                            target_string=path,
                            mandatory_fragments=[
                                f"field_name=continuation_sheet_{page}"
                            ],
                            one_of_fragments=["meta=lpc", "meta=lpc_lp", "meta=pfa_c"],
                        ):
                            pages[page]["path"] = path
                            if "meta=pfa_c" in path:
                                pages[page]["type"] = "unknown"

        for page in ["p1", "p2"]:
            if len(checked_checkboxes[page]) > 1:
                logger.warning(
                    f"User has ticked more than one checkbox for page {page} of path {path_filter}"
                )
            # If type is not unknown, make type neither where no checkboxes ticked or the last type ticked otherwise
            if pages[page]["type"] != "unknown":
                pages[page]["type"] = (
                    "neither"
                    if not checked_checkboxes[page]
                    else checked_checkboxes[page][-1]
                )
            if pages[page]["path"] == "":
                pages.pop(page)

        return pages

    @staticmethod
    def merge_continuation_images_into_path_selection(
        path_selection, continuation_sheets
    ) -> dict:
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
                elif pagenumber_dict["type"] == "unknown":
                    instructions_continuation_count += 1
                    key = f"continuation_unknown_{instructions_continuation_count}"
                else:
                    continue
                # Add the page path to the corresponding key in final_path_selection
                path_selection[key] = pagenumber_dict["path"]

        return path_selection

    @staticmethod
    def string_fragments_in_string(
        target_string, mandatory_fragments, one_of_fragments
    ) -> bool:
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

        (thresh, im_bw) = cv2.threshold(
            img, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
        )

        # Mask always seems to be black so we invert so mask and background match
        im_bw_inverted = cv2.bitwise_not(im_bw)
        # Define the size of the image and the size of the border to ignore
        img_height, img_width = im_bw_inverted.shape

        border_size = int(min(img_height, img_width) * 0.2)

        # Create a mask to ignore the border
        mask = np.zeros((img_height, img_width), np.uint8)
        mask[
            border_size : img_height - border_size,
            border_size : img_width - border_size,
        ] = 255

        # Apply the mask to the image
        im_bw_inverted = cv2.bitwise_and(im_bw_inverted, im_bw_inverted, mask=mask)

        number_of_white_pix = np.sum(
            im_bw_inverted == 255
        )  # extracting only white pixels
        number_of_black_pix = np.sum(im_bw_inverted == 0)
        total_pixels = number_of_white_pix + number_of_black_pix
        percentage_black = number_of_black_pix / total_pixels

        is_ticked = False if percentage_black > 0.99 else True
        logger.debug(f"Checkbox is {str(is_ticked)} for: {image_path}")

        # If the percentage_black (as image is inverted) is above a certain threshold, the image is blank
        return False if percentage_black > 0.99 else True
