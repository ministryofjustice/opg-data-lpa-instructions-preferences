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


def remove_specks(
    image, min_contour_area: int = 10, adaptive_thresholding: bool = False
) -> np.ndarray:
    gray = convert_img_to_grayscale(image)
    thresh = (
        cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 18
        )
        if adaptive_thresholding
        else cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    )

    cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    for c in cnts:
        if cv2.contourArea(c) < min_contour_area:
            cv2.drawContours(thresh, [c], -1, (0, 0, 0), -1)

    result = 255 - thresh

    return result
