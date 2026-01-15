import cv2

from numpy import ndarray
from pydantic import BaseModel
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Union


class BaseOcrEngine(ABC, BaseModel):
    rotation_lookup: Optional[Dict[str, int]] = {
        "90": cv2.ROTATE_90_COUNTERCLOCKWISE,
        "180": cv2.ROTATE_180,
        "270": cv2.ROTATE_90_CLOCKWISE,
    }
    minimum_orientation_confidence: Optional[float] = 1.5

    @abstractmethod
    def extract_text_from_images(images: List[ndarray]):
        ...

    @abstractmethod
    def auto_rotate_images(images: List[ndarray]):
        ...

    def _rotate_image(
        self,
        image: ndarray,
        rotation: Union[int, None],
        confidence: Union[int, None],
    ):
        rimg = image
        if rotation is not None and confidence is not None and rotation != 0:
            if confidence > self.minimum_orientation_confidence:
                rimg = cv2.rotate(image, self.rotation_lookup[str(rotation)])

        return rimg

    def _rotate_images(
        self, images: List[ndarray], rotation_arguments: List[Tuple[int, int]]
    ):
        return [
            self._rotate_image(image, *rotation_arguments)
            for image, rotation_arguments in zip(
                images,
                rotation_arguments,
            )
        ]
