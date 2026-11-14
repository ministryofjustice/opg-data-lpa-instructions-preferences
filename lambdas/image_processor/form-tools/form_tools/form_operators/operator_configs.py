from pydantic import BaseModel, Field, validator
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


class SimilarityConfig(BaseModel):
    """RANSAC tolerance in template pixels and maximum fine rotation in degrees."""

    threshold: float = Field(default=3, gt=0, allow_inf_nan=False)
    max_rotation_degrees: float = Field(default=20, gt=0, le=45, allow_inf_nan=False)

    class Config:
        extra = "forbid"


class FormOperatorConfig(BaseModel):
    """Config for a `FormOperator`

    Attributes:
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
            to calculate a similarity transform
        proportion (float): The proportion
            of keypoint matches to keep or
            the proportion to use in a KNN ratio
            test
        knn (int): The number of nearest neighbours to
            return as part of a KNN match procedure
    """

    detector: DetectorConfig
    matcher: MatcherConfig
    minimum_matches: Optional[int] = 10
    similarity_options: SimilarityConfig = Field(default_factory=SimilarityConfig)
    proportion: Optional[float] = 1.0
    knn: Optional[int] = 2
