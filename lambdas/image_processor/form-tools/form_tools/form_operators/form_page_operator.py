import os
import re
import cv2
import yaml
import importlib
import numpy as np

from pathlib import Path
from pydantic import BaseModel
from typing import Union, List, Tuple, Optional

from .operator_configs import (
    FormOperatorConfig,
    OcrConfig,
    HomographyConfig,
    PreprocessingTransform,
)
from . import __name__ as module_name
from ..form_meta.form_meta import FormPage
from .preprocessors import convert_img_to_grayscale


class FormPageOperator(BaseModel):
    """Operator for a single form page

    Applies transformations to an instance (image, image text) of
    a form page. Transformations including aligning an image to
    a form page template image.

    Attributes:
        config (FormOperatorConfig): A form operator config
            for setting up image transformations
        detector (Union[cv2.ORB, cv2.SIFT]): A opencv
            detector object
        matcher (cv2 Matcher): An opencv matcher object
        proportion (float): Proportion of keypoint matches
            to keep or to use in KNN ratio test
        ocr_options (OcrConfig): OCR engine
            choices for form operator
        minimum_matches (int): The minimum number of
            good keypoint matches to allow homography
            matrix to be computed
        preprocessing_transforms (Union[List[PreprocessingTransform], None]):
            List of transformations and their arguments
            to apply to the images before processing
    """

    config: FormOperatorConfig

    @property
    def detector(self) -> Union[cv2.ORB, cv2.SIFT]:
        detector_config = self.config.detector

        detector_name = detector_config.name
        detector_args = detector_config.args if detector_config.args is not None else []
        detector_kwargs = (
            detector_config.kwargs if detector_config.kwargs is not None else {}
        )

        try:
            method_name = f"{detector_name}_create"
            create_detector = getattr(cv2, method_name)

            detector = create_detector(*detector_args, **detector_kwargs)

        except Exception:
            raise ValueError(
                "Cannot create detector with given config:\n" + str(detector_config)
            )

        return detector

    @property
    def matcher(self):
        matcher_config = self.config.matcher

        matcher_id = matcher_config.id
        matcher_args = matcher_config.args if matcher_config.args is not None else []
        matcher_kwargs = (
            matcher_config.kwargs if matcher_config.kwargs is not None else {}
        )

        try:
            if isinstance(matcher_id, int):
                matcher = cv2.DescriptorMatcher_create(
                    matcher_id, *matcher_args, **matcher_kwargs
                )
            elif matcher_id == "BF":
                matcher = cv2.BFMatcher(*matcher_args, **matcher_kwargs)
            elif matcher_id == "FLANN":
                matcher = cv2.FlannBasedMatcher(*matcher_args, **matcher_kwargs)
            else:
                raise ValueError(
                    "Matcher dictionary config does not\n" "have a recognised cv2 id."
                )

        except Exception:
            raise ValueError(
                "Matcher dictionary config does not\n" "have a recognised cv2 id."
            )

        return matcher

    @property
    def knn(self) -> Union[int, None]:
        return self.config.knn

    @property
    def proportion(self) -> float:
        return self.config.proportion

    @property
    def ocr_options(self) -> OcrConfig:
        return self.config.ocr_options

    @property
    def minimum_matches(self) -> Union[int, None]:
        return self.config.minimum_matches

    @property
    def homography_options(self) -> Union[HomographyConfig, None]:
        return self.config.homography_options

    @property
    def preprocessing_transforms(self) -> Union[List[PreprocessingTransform], None]:
        return self.config.preprocessing_transforms

    @classmethod
    def create_from_config(
        cls,
        config: Union[str, dict, FormOperatorConfig],
    ):
        """Creates a `FormPageOperator` from a config

        Takes a `FormOperatorConfig` to create an
        instance of a `FormPageOperator`. Config
        can be provided as a path to a valid config
        yaml file, a yaml string, dictionary or
        `FormOperatorConfig` object.

        Params:
            config (Union[str, dict, FormOperatorConfig]):
                An object pointing to or representing
                a valid `FormOperatorConfig`

        Returns:
            (FormPageOperator): An instantiated
                `FormPageOperator` object with
                the given config
        """
        if isinstance(config, FormOperatorConfig):
            operator = cls(config=config)

        elif isinstance(config, dict):
            operator_config = FormOperatorConfig(**config)
            operator = cls(config=operator_config)

        else:
            config = cls._read_config(config)
            operator = cls(config=config)

        return operator

    @staticmethod
    def _read_config(config: str) -> FormOperatorConfig:
        """Reads config from string or path

        Instantiates a `FormOperatorConfig` object
        from a config string or path to a valid
        config yaml file.

        Params:
            config (str):
                An string representing
                a valid `FormOperatorConfig` or
                a path to a valid config yaml file

        Returns:
            (FormOperatorConfig): A
                `FormPageOperator` config from
                the original string or file.
        """
        config_path = Path(config)
        if config_path.suffix in [".yml", ".yaml"]:
            with open(config_path, "r") as f:
                config_dict = yaml.safe_load(f)

        else:
            config_dict = yaml.safe_load(config)

        config = FormOperatorConfig(**config_dict)

        return config

    @staticmethod
    def check_image_text_against_form_page(form_page: FormPage, image_str: str) -> bool:
        """Checks if image matches given `FormPage`

        Takes the OCR text of an form page image and checks
        if it matches the identifier of a given `FormPage`
        object.

        Params:
            form_page (FormPage):
                A `FormPage` object representing
                the metadata for a form page
            image_str (str): The text representation
                of an image provided by an OCR engine

        Returns:
            (bool): Whether the image matches the given
                form page identifier
        """
        page_regex = form_page.identifier

        return (
            True if re.search(page_regex, image_str, re.DOTALL) is not None else False
        )

    def _return_matches(
        self,
        page_image_descriptions: np.ndarray,
        page_template_image_descriptions: np.ndarray,
    ) -> List[cv2.DMatch]:
        """Helper method that returns keypoint matches

        Takes candidate keypoint descriptions for a form
        page image and form page template image and returns
        a set of matching keypoints. Uses the loaded config
        to determine whether to apply a ratio test etc.

        Params:
            page_image_descriptions (np.ndarray):
                keypoint descriptions for a form page image
            page_template_image_descriptions (np.ndarray):
                keypoint descriptions for a form page template image

        Returns:
            (List[cv2.DMatch]): List of opencv match objects
        """
        matcher = self.matcher
        k = self.knn
        p = self.proportion

        if k is not None and k > 1:
            matches = matcher.knnMatch(
                page_image_descriptions, page_template_image_descriptions, k=k
            )
            good = []
            for match in matches:
                m = match[0]
                n = match[1]
                if m.distance < p * n.distance:
                    good.append(m)

            good = sorted(good, key=lambda x: x.distance)

        else:
            matches = (
                matcher.match(
                    page_image_descriptions, page_template_image_descriptions, None
                )
                if k is None or k < 1
                else [
                    m[0]
                    for m in matcher.knnMatch(
                        page_image_descriptions, page_template_image_descriptions, k
                    )
                ]
            )

            matches = sorted(matches, key=lambda x: x.distance)

            keep = int(len(matches) * p)
            good = matches[:keep]

        return good

    def _find_homography(
        self,
        keypoint_matches: List[cv2.DMatch],
        page_image_keypoints: Tuple[cv2.KeyPoint, ...],
        page_template_image_keypoints: Tuple[cv2.KeyPoint, ...],
    ) -> np.ndarray:
        """Helper method to find the homography matrix between two images

        Takes keypoints for a form page image and it's template, as well
        as keypoint matches, and calculates the homography matrix
        required to align the image with it's template.

        Params:
            keypoint_matches (List[cv2.DMatch]): A list
                of keypoint match objects between the two
                images
            page_image_keypoints (np.ndarray):
                keypoints for a form page image
            page_template_image_keypoints (np.ndarray):
                keypoints for a form page template image

        Returns:
            (np.ndarray): A homography matrix
        """
        src_pts = np.float32(
            [page_image_keypoints[m.queryIdx].pt for m in keypoint_matches]
        ).reshape(-1, 1, 2)

        dst_pts = np.float32(
            [page_template_image_keypoints[m.trainIdx].pt for m in keypoint_matches]
        ).reshape(-1, 1, 2)

        if self.homography_options is not None:
            homography_kwargs = {
                "method": cv2.RANSAC
                if self.homography_options.method is None
                else self.homography_options.method,
                "ransacReprojThreshold": 3
                if self.homography_options.threshold is None
                else self.homography_options.threshold,
            }
        else:
            homography_kwargs = {"method": cv2.RANSAC}

        H, _ = cv2.findHomography(src_pts, dst_pts, **homography_kwargs)

        return H

    def _check_homography_singular(
        self,
        homography_matrix: np.ndarray,
    ) -> bool:
        """Helper to determine if a homography matrix is degenerate

        Takes a homography matrix and checks whether it's determinant
        is near enough to 0 to be considered singular. Whether the
        determinant is 'near enough' is determined by the
        `singular_matrix_threshold` provided in the `homography_options`
        in the config.

        Params:
            homography_matrix (ndarray): A
                ndarray representing a
                homography matrix between an
                image and it's template

        Returns:
            (bool): Whether the matrix is considered degenerate
        """
        abs_detH = np.absolute(np.linalg.det(homography_matrix))

        homography_options = self.homography_options
        degenerate_threshold = (
            None
            if homography_options is None
            else homography_options.dict().get("singular_matrix_threshold")
        )

        check = (
            False if degenerate_threshold is None else abs_detH < degenerate_threshold
        )

        return check

    def _show_debug_images(
        self,
        page_image: np.ndarray,
        page_image_keypoints: np.ndarray,
        page_template_image: np.ndarray,
        page_template_image_keypoints: np.ndarray,
        keypoint_matches: List[cv2.DMatch],
        aligned_page_image: np.ndarray,
    ):
        """Helper to determine if a homography matrix is degenerate

        Takes a homography matrix and checks whether it's determinant
        is near enough to 0 to be considered singular. Whether the
        determinant is 'near enough' is determined by the
        `singular_matrix_threshold` provided in the `homography_options`
        in the config.

        Params:
            homography_matrix (ndarray): A
                ndarray representing a
                homography matrix between an
                image and it's template

        Returns:
            (bool): Whether the matrix is considered degenerate
        """
        if "PYTEST_TEST_ENV" not in os.environ:
            cv2.startWindowThread()

        matchedVis = cv2.drawMatches(
            page_image,
            page_image_keypoints,
            page_template_image,
            page_template_image_keypoints,
            keypoint_matches,
            None,
        )

        if "PYTEST_TEST_ENV" not in os.environ:
            cv2.imshow("Matched Keypoints", matchedVis)
            cv2.waitKey(0)

        stacked = np.hstack([aligned_page_image, page_template_image])

        overlay = page_template_image.copy()
        output = aligned_page_image.copy()

        cv2.addWeighted(overlay, 0.5, output, 0.5, 0, output)

        if "PYTEST_TEST_ENV" not in os.environ:
            # show the two output image alignment visualizations
            cv2.imshow("Image Alignment Stacked", stacked)
            cv2.imshow("Image Alignment Overlay", output)
            cv2.waitKey(0)

    def align_image_to_template(
        self,
        page_image: np.ndarray,
        page_template_image: np.ndarray,
        form_page: Optional[Union[FormPage, None]] = None,
        page_image_str: Optional[Union[str, None]] = None,
        debug: Optional[bool] = False,
    ) -> np.ndarray:
        """Alignes a form page image to a template image

        Takes a form page image along with it's OCR text and
        attempts to align it with a given form page template
        image. Returns the aligned template.

        Params:

            page_image (ndarray): An opencv image
                of the form page
            page_template_image (ndarray): An opencv image
                of the form page template
            form_page (Optional[Union[FormPage, None]]):
                A `FormPage` object representing
                the metadata for a form page
            page_image_str (Optional[Union[str, None]]): The text representation
                of an image provided by an OCR engine
            debug (Optional[bool]): Whether to show aligned
                images as the method is run

        Returns:
            (ndarray): The aligned form page image
        """
        if form_page is not None and page_image_str is not None:
            if not self.check_image_text_against_form_page(form_page, page_image_str):
                raise ValueError(
                    "Cannot align an image that\n"
                    "doesn't correspond to expected template"
                )

        page_template_image = convert_img_to_grayscale(page_template_image)

        detector = self.detector
        kps_img, descs_img = detector.detectAndCompute(page_image, None)
        kps_tmpt, descs_tmpt = detector.detectAndCompute(page_template_image, None)

        good = self._return_matches(descs_img, descs_tmpt)

        if len(good) > self.minimum_matches:
            H = self._find_homography(good, kps_img, kps_tmpt)
            singular = self._check_homography_singular(H)

            if singular:
                raise RuntimeError("Failed to generate a valid homography matrix")

            h, w = page_template_image.shape[:2]

            aligned = cv2.warpPerspective(page_image, H, (w, h))

            if debug:
                self._show_debug_images(
                    page_image, kps_img, page_template_image, kps_tmpt, good, aligned
                )

            return aligned

        else:
            raise RuntimeError(
                "There were not enough keypoints matched\n"
                "between the image and the template."
            )
