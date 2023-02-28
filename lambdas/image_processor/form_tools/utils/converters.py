import re
import cv2
import base64
import numpy as np

from PIL import Image
from typing import Optional, Tuple


def _validate_cv2(image):
    if not isinstance(image, np.ndarray):
        raise TypeError("Image is not a valid cv2\n" "image object")


def _validate_PIL(image):
    image_type = str(type(image))
    if re.search("PIL\\..*Image", image_type) is None:
        raise TypeError("Image is not a valid PIL\n" "image object.")


def validate(image):
    try:
        _validate_cv2(image)
        _validate_PIL(image)
    except TypeError:
        raise TypeError("Image is not a valid PIL\n" "or cv2 image object.")


def convert_PIL_to_cv2(image):
    _validate_PIL(image)
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def convert_cv2_to_PIL(image):
    _validate_cv2(image)
    return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))


def convert_cv2_to_bytes(image: np.ndarray):
    image_bytes = image.tobytes()
    bpp = image.shape[2] if len(image.shape) == 3 else 1
    h, w = image.shape[0:2]
    bpl = bpp * w
    return image_bytes, w, h, bpp, bpl


def convert_bytes_to_cv2(image_args: Tuple[bytes, int, int, int, int]):
    image, w, h, bpp, bpl = image_args
    rimage = np.frombuffer(image, dtype=np.uint8).reshape(h, w, bpp)
    rbpp = rimage.shape[2] if len(rimage.shape) == 3 else 1
    if rimage.shape[1] * rbpp != bpl:
        raise ValueError("Failed conversion from bytes")
    return rimage


def convert_image_string_to_cv2(
    image_args: Tuple[str, int, int, int, int], encode_format: Optional[str] = "UTF-8"
):
    image_string, w, h, bpp, bpl = image_args
    bimage = base64.b64decode(image_string.encode(encode_format))
    rimage = convert_bytes_to_cv2((bimage, w, h, bpp, bpl))
    return rimage


def convert_cv2_to_image_string(image, encode_format: Optional[str] = "UTF-8"):
    bimage, w, h, bpp, bpl = convert_cv2_to_bytes(image)
    image_string = base64.b64encode(bimage).decode(encode_format)
    return image_string, w, h, bpp, bpl
