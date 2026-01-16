import cv2

from pydantic import BaseModel, validator
from typing import Dict, List, Optional, Any, Union


class DetectorConfig(BaseModel):
    """Config for opencv detector

    Attributes:
        name (str): Name of the detector,
            either SIFT or ORB
        args (Optional[List[Any]]):
            Agruments to pass to the
            opencv detector at creation
        kwargs (Optional[Dict[str, Any]]):
            Keyword arguments to pass to
            opencv detector at creation
    """

    name: str
    args: Optional[List[Any]]
    kwargs: Optional[Dict[str, Any]]

    @validator("name", allow_reuse=True)
    def _validate_name(cls, v):
        assert v in ["SIFT", "ORB"], (
            "Detector config must include a name key\n"
            "with either SIFT or ORB specified."
        )
        return v


class MatcherConfig(BaseModel):
    """Config for opencv detector

    Attributes:
        id (Union[int, str]): id for
            an opencv matcher
        args (Optional[List[Any]]):
            Agruments to pass to the
            opencv matcher at creation
        kwargs (Optional[Dict[str, Any]]):
            Keyword arguments to pass to
            opencv matcher at creation
    """

    id: Union[int, str]
    args: Optional[List[Any]]
    kwargs: Optional[Dict[str, Any]]

    @validator("id", allow_reuse=True)
    def _validate_id(cls, v):
        if isinstance(v, str):
            assert v in ["BF", "FLANN"], (
                "Matcher config must be an integer\n" "or set to BF or FLANN"
            )
        return v


class HomographyConfig(BaseModel):
    """Config for opencv homography matrix creator

    Attributes:
        method (Optional[int]): A valid
            homography method to pass to
            `cv2.findHomography`
        threshold (Optional[Union[float, None]]):
            A homography threshold to pass
            to `cv2.findHomography`
        singular_matrix_threshold (Optional[Union[float, None]]):
            A threshold to determine whether a given
            homography matrix is degenerate - the threshold
            is compared against the absolute value of the
            determinant of the matrix
    """

    method: Optional[int] = cv2.RANSAC
    threshold: Optional[Union[float, None]] = None
    singular_matrix_threshold: Optional[Union[float, None]] = None


class OcrConfig(BaseModel):
    """Config for OCR engine options

    Attributes:
        rotation_engine (str): Choice of OCR engine
            to perform auto rotation
        text_extraction_engine (str): Choice of OCR
            engine to perform text extraction
        minimum_orientation_confidence (Optional[float]):
            The minimum confidence by which to accept
            an autorotation result
    """

    rotation_engine: str
    text_extraction_engine: str
    minimum_orientation_confidence: Optional[float] = 1.5


class PreprocessingTransform(BaseModel):
    """Config for a preprocessing transformation

    Attributes:
        name (str): Name of the preprocessing
            transformation as included in
            `form_tools.form_operators.preprocessors`
        args (Optional[List[Any]]):
            Agruments to pass to the
            transformation
        kwargs (Optional[Dict[str, Any]]):
            Keyword arguments to pass to
            the transformation
    """

    name: str
    args: Optional[Union[List[Any], None]] = None
    kwargs: Optional[Union[Dict[str, Any], None]] = None


class FormOperatorConfig(BaseModel):
    """Config for a `FormOperator`

    Attributes:
        ocr_options (OcrConfig): An `OcrConfig`
            object for deciding which engines
            to use on the form
        detector (DetectorConfig):
            A `DetectorConfig` object for
            deciding which opencv detector to use
            as part of form-template alignment
        matcher (MatcherConfig):
            A `MatcherConfig` object for
            deciding which opencv matcher to use
            as part of form-template alignment
        minimum_matches (int):
            An integer representing the minimum
            number of keypoint matches for proceeding
            to calculate a homography matrix
        proportion (float): The proportion
            of keypoint matches to keep or
            the proportion to use in a KNN ratio
            test
        knn (int): The number of nearest neighbours to
            return as part of a KNN match procedure
        preprocessing_transforms ([List[PreprocessingTransform], None]]):
            List of `PreprocessingTransform` objects for applying
            preprocessing transforms to a form image
    """

    ocr_options: OcrConfig
    detector: DetectorConfig
    matcher: MatcherConfig
    minimum_matches: Optional[int] = 10
    homography_options: Optional[Union[HomographyConfig, None]] = None
    proportion: Optional[float] = 1.0
    knn: Optional[int] = 2
    preprocessing_transforms: Optional[Union[List[PreprocessingTransform], None]] = None
