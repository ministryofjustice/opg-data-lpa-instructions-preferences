import cv2
import numpy as np

from PIL import Image
from pdf2image import convert_from_bytes
from typing import List, Optional, ByteString, Dict, Any
import uuid

class ImageReader:
    """ImageReader utility class

    General purpose class for reading PDF files from a local
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
            (str): file path to file containing the ndarray
        """
        file_name = f"/tmp/{str(uuid.uuid4())}.npy"

        image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        np.save(file_name, image)

        return file_name

    @staticmethod
    def _read_bytes(file_path: str) -> ByteString:
        """Reads raw bytes from image file

        Reads an image as raw bytes from a local filepath

        Params:
            file_path (str): Local filepath to image

        Returns:
            (ByteString): Byte string for image
        """
        with open(file_path, "rb") as img_file:
            raw_img = img_file.read()

        return raw_img

    @classmethod
    def read(
        cls,
        file_path: str,
        conversion_parameters: Optional[Dict[str, Any]] = None,
        **bytes_kwargs,
    ) -> List[np.ndarray]:
        """reader method

        The reader method for pdf image files. Uses `pdf2image`
        `convert_from_bytes` to convert a pdf byte string to
        a list of opencv images saved as .npy files.

        Params:
            file_path (str): Local filepath to image
            conversion_parameters (Optional[Dict[str, Any]]):
                Options to pass to `pdf2image.convert_from_bytes`
            **bytes_kwargs: Optional keyword arguments to pass onto
                `_read_bytes` method.

        Returns:
            Tuple[bool, List[str]]: Tuple where
                first entry specifies whether the result
                is a multipage image, and the second the
                list of file paths containing the ndarrays of the images
        """

        raw_img = cls._read_bytes(file_path, **bytes_kwargs)
        if conversion_parameters is None:
            conversion_parameters = {}

        converted_imgs = convert_from_bytes(raw_img, **conversion_parameters)

        img_locations = []

        if isinstance(converted_imgs, list):
            for image in converted_imgs:
                file_name = f"/tmp/{str(uuid.uuid4())}.jpg"
                image.save(f"{file_name}", "JPEG")
                img_locations.append(file_name)
            multipage = True if len(converted_imgs) > 1 else False
        else:
            file_name = f"/tmp/{str(uuid.uuid4())}.jpg"
            converted_imgs.save(f"{file_name}", "JPEG")
            img_locations.append(file_name)
            multipage = False

        return multipage, img_locations
