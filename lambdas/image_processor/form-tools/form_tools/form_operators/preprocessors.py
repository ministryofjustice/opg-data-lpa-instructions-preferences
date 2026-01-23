import cv2
import numpy as np

from ..utils.converters import (
    _validate_cv2,
    _validate_PIL,
    convert_PIL_to_cv2,
    convert_cv2_to_PIL,
)


def convert_img_to_grayscale(image, return_as_PIL=False):
    try:
        _validate_PIL(image)
        image = convert_PIL_to_cv2(image)
    except TypeError:
        _validate_cv2(image)

    if len(image.shape) != 2:
        image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        image_gray = image

    if return_as_PIL:
        image_gray = convert_cv2_to_PIL(image_gray)

    return image_gray

