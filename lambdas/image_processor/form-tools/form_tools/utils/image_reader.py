import os
import cv2
import boto3
import tempfile
import numpy as np
import awswrangler as wr

from PIL import Image
from glob import glob
from pathlib import Path
from pdf2image import convert_from_bytes
from typing import List, Tuple, Union, Optional, ByteString, Dict, Any


class ImageReader:
    """ImageReader utility class

    General purpose class for reading image files from a local
    path.
    """

    @staticmethod
    def _convert_PIL_to_cv2(image: Image) -> np.ndarray:
        """Convert Pillow image to a opencv image

        Takes a Pillow image and returns an numpy
        ndarray corresponding to an opencv image.

        Params:
            image (Image): A Pillow image

        Returns:
            (ndarray): Numpy ndarray opencv image
        """
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    @staticmethod
    def _read_bytes(
        file_path: str,
    ) -> ByteString:
        """Reads raw bytes from image file

        Reads an image as raw bytes from a local filepath.

        Params:
            file_path (str): Local filepath to image

        Returns:
            (ByteString): Byte string for image
        """
        with open(file_path, "rb") as img_file:
            raw_img = img_file.read()

        return raw_img

    @classmethod
    def read(cls, file_path: str) -> Tuple[bool, List[np.ndarray]]:
        """Reads an image file

        Reads an image file locally.

        Params:
            file_path (str): Local directory path

        Returns:
            Tuple[bool, List[ndarray]]: Tuple where
                first entry specifies whether the result
                is a multipage image, and the second the
                list of images returned

        """
        raw_img = cls._read_bytes(file_path)
        nparr = np.frombuffer(raw_img, np.uint8)
        img =  cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return (False, [img])
