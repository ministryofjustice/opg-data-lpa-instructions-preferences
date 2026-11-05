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
    SimilarityConfig,
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
        minimum_matches (int): The minimum number of
            good keypoint matches to estimate page registration
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
    def minimum_matches(self) -> Union[int, None]:
        return self.config.minimum_matches

    @property
    def similarity_options(self) -> SimilarityConfig:
        return self.config.similarity_options

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

        if page_image_descriptions is None or page_template_image_descriptions is None:
            raise RuntimeError("No image features available for page alignment")
        if k is not None and k > 1:
            matches = matcher.knnMatch(
                page_image_descriptions, page_template_image_descriptions, k=k
            )
            good = []
            for match in matches:
                if len(match) < 2:
                    continue
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

    def _find_similarity(
        self,
        keypoint_matches: List[cv2.DMatch],
        page_image_keypoints: Tuple[cv2.KeyPoint, ...],
        page_template_image_keypoints: Tuple[cv2.KeyPoint, ...],
        page_image_shape: Tuple[int, ...],
        page_template_image_shape: Tuple[int, ...],
    ) -> np.ndarray:
        """Estimate rotation, translation and uniform scale, never shear or perspective."""
        src_pts = np.float32(
            [page_image_keypoints[m.queryIdx].pt for m in keypoint_matches]
        ).reshape(-1, 1, 2)

        dst_pts = np.float32(
            [page_template_image_keypoints[m.trainIdx].pt for m in keypoint_matches]
        ).reshape(-1, 1, 2)

        matrix, mask = cv2.estimateAffinePartial2D(
            src_pts,
            dst_pts,
            method=cv2.RANSAC,
            ransacReprojThreshold=self.similarity_options.threshold,
        )

        if matrix is None or mask is None or not np.isfinite(matrix).all():
            raise RuntimeError("Failed to generate a valid similarity transform")

        inliers = mask.ravel().astype(bool)
        if np.count_nonzero(inliers) <= self.minimum_matches or np.mean(inliers) < 0.25:
            raise RuntimeError("Insufficient inlier support for page alignment")

        for points, shape in (
            (src_pts, page_image_shape),
            (dst_pts, page_template_image_shape),
        ):
            coverage = cv2.contourArea(cv2.convexHull(points[inliers])) / (
                shape[0] * shape[1]
            )
            if coverage < 0.1:
                raise RuntimeError("Alignment inliers cover too little of the page")

        residuals = np.linalg.norm(
            cv2.transform(src_pts[inliers], matrix) - dst_pts[inliers], axis=2
        )
        if np.median(residuals) > self.similarity_options.threshold:
            raise RuntimeError("Page alignment residuals exceed the allowed tolerance")
        return matrix

    def _check_similarity_geometry(
        self,
        matrix: np.ndarray,
        page_image_shape: Tuple[int, ...],
        page_template_image_shape: Tuple[int, ...],
    ) -> None:
        h, w = page_image_shape[:2]
        if matrix.shape != (2, 3) or not np.isfinite(matrix).all():
            raise RuntimeError("Invalid similarity transform")
        linear = matrix[:, :2]
        a, b = linear[0]
        if not np.allclose(linear, [[a, b], [-b, a]], rtol=1e-6, atol=1e-9):
            raise RuntimeError("Page alignment must not contain shear or reflection")
        scale = np.hypot(a, b)
        rotation = abs(np.degrees(np.arctan2(b, a)))
        if rotation > self.similarity_options.max_rotation_degrees:
            raise RuntimeError("Page alignment rotation exceeds the allowed limit")
        th, tw = page_template_image_shape[:2]
        if not (0.5 <= scale * w / tw <= 2 and 0.5 <= scale * h / th <= 2):
            raise RuntimeError("Page alignment scale exceeds the allowed limit")
        corners = np.float64([[0, 0], [w, 0], [w, h], [0, h]])
        projected = (np.column_stack((corners, np.ones(4))) @ matrix.T).astype(
            np.float32
        )
        normalized = projected / np.float32([tw, th])
        if not np.isfinite(normalized).all():
            raise RuntimeError("Page alignment has non-finite page coordinates")
        area = cv2.contourArea(normalized, oriented=True)
        edges = np.roll(normalized, -1, axis=0) - normalized
        lengths = np.linalg.norm(edges, axis=1)
        overlap, _ = cv2.intersectConvexConvex(
            projected, np.float32([[0, 0], [tw, 0], [tw, th], [0, th]])
        )
        if (
            not cv2.isContourConvex(normalized)
            or not 0.25 <= area <= 4
            or np.any(lengths < 0.5)
            or np.any(lengths > 2)
            or np.any(normalized < -0.5)
            or np.any(normalized > 1.5)
            or overlap / (tw * th) < 0.75
        ):
            raise RuntimeError("Page alignment would excessively distort the image")

    def _show_debug_images(
        self,
        page_image: np.ndarray,
        page_image_keypoints: np.ndarray,
        page_template_image: np.ndarray,
        page_template_image_keypoints: np.ndarray,
        keypoint_matches: List[cv2.DMatch],
        aligned_page_image: np.ndarray,
    ):
        """Display feature matches and the aligned page overlay."""
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
        kps_img, descs_img = detector.detectAndCompute(
            convert_img_to_grayscale(page_image), None
        )
        kps_tmpt, descs_tmpt = detector.detectAndCompute(page_template_image, None)

        good = self._return_matches(descs_img, descs_tmpt)

        if len(good) > self.minimum_matches:
            matrix = self._find_similarity(
                good,
                kps_img,
                kps_tmpt,
                page_image.shape,
                page_template_image.shape,
            )
            self._check_similarity_geometry(
                matrix, page_image.shape, page_template_image.shape
            )
            h, w = page_template_image.shape[:2]

            aligned = cv2.warpAffine(
                page_image,
                matrix,
                (w, h),
                borderValue=255 if page_image.ndim == 2 else (255, 255, 255),
            )

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
