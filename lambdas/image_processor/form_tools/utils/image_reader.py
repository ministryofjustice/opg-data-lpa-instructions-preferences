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
from dataengineeringutils3.s3 import s3_path_to_bucket_key
from typing import List, Tuple, Union, Optional, ByteString, Dict, Any

from .constants import aws_default_region


class ImageReader:
    """ImageReader utility class

    General purpose class for reading image files from a local
    path or from an AWS S3 bucket. The reader can also handle
    reading multi-page image formats if saved as pdf or tif.

    Attributes:
        multi_page_formats (List[str]): List of multi page image
            formats supported by the class
    """

    multi_page_formats = [".pdf", ".tif"]

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
        file_path: str, s3_client: Optional[Union[boto3.client, None]] = None
    ) -> ByteString:
        """Reads raw bytes from image file

        Reads an image as raw bytes from either a
        local filepath or an AWS S3 location.

        Params:
            file_path (str): Local or s3 filepath to image
            s3_client (Optional[Union[boto3.client, None]]):
                boto3 s3 client

        Returns:
            (ByteString): Byte string for image
        """
        if file_path.startswith("s3://"):
            if "AWS_DEFAULT_REGION" not in os.environ:
                os.environ["AWS_DEFAULT_REGION"] = aws_default_region

            if s3_client is None:
                s3_client = boto3.client("s3")

            b, k = s3_path_to_bucket_key(file_path)

            raw_img = s3_client.get_object(Bucket=b, Key=k).get("Body").read()

        else:
            with open(file_path, "rb") as img_file:
                raw_img = img_file.read()

        return raw_img

    @classmethod
    def _read_default(cls, file_path: str, **bytes_kwargs) -> np.ndarray:
        """Default image reader method

        The default reader method for an image file. First
        reads the image in as a byte string before converting
        into an opencv numpy ndarray image.

        Params:
            file_path (str): Local or s3 filepath to image
            **bytes_kwargs: Optional keyword arguments to pass onto
                `_read_bytes` method.

        Returns:
            (ByteString): Byte string for image
        """
        raw_img = cls._read_bytes(file_path, **bytes_kwargs)
        nparr = np.frombuffer(raw_img, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img

    @staticmethod
    def _read_tif(file_path: str, **multiread_kwargs) -> Tuple[bool, List[np.ndarray]]:
        """tif image reader method

        The reader method for tif image files. If the file
        is located in S3, it will first be downloaded to
        a temporary file before being read in by
        `cv2.imreadmulti`.

        Params:
            file_path (str): Local or s3 filepath to image
            **bytes_kwargs: Optional keyword arguments to pass onto
                `_read_bytes` method.

        Returns:
            Tuple[bool, List[ndarray]]: Tuple where
                first entry specifies whether the result
                is a multipage image, and the second the
                list of images returned
        """
        if file_path.startswith("s3://"):
            _, tmp = tempfile.mkstemp(suffix=".tif")
            wr.s3.download(path=file_path, local_file=tmp)
            _, imgs = cv2.imreadmulti(tmp, **multiread_kwargs)
            os.remove(tmp)
        else:
            _, imgs = cv2.imreadmulti(file_path, **multiread_kwargs)

        multipage = True
        if isinstance(imgs, tuple):
            if len(imgs) == 1:
                imgs = [imgs[0]]
                multipage = False
        else:
            raise TypeError("Expecting tuple to be returned by\n" "imreadmulti.")

        return multipage, list(imgs)

    @classmethod
    def _read_pdf(
        cls,
        file_path: str,
        conversion_parameters: Optional[Dict[str, Any]] = None,
        **bytes_kwargs,
    ) -> List[np.ndarray]:
        """pdf image reader method

        The reader method for pdf image files. Uses `pdf2image`
        `convert_from_bytes` to convert a pdf byte string to
        a list of opencv images.

        Params:
            file_path (str): Local or s3 filepath to image
            conversion_parameters (Optional[Dict[str, Any]]):
                Options to pass to `pdf2image.convert_from_bytes`
            **bytes_kwargs: Optional keyword arguments to pass onto
                `_read_bytes` method.

        Returns:
            Tuple[bool, List[ndarray]]: Tuple where
                first entry specifies whether the result
                is a multipage image, and the second the
                list of images returned
        """
        raw_img = cls._read_bytes(file_path, **bytes_kwargs)
        if conversion_parameters is None:
            conversion_parameters = {}

        converted_imgs = convert_from_bytes(raw_img, **conversion_parameters)

        if isinstance(converted_imgs, list):
            cv2_images = [cls._convert_PIL_to_cv2(img) for img in converted_imgs]
            multipage = True if len(cv2_images) > 1 else False
        else:
            cv2_images = [cls._convert_PIL_to_cv2(converted_imgs)]
            multipage = False

        return multipage, cv2_images

    @classmethod
    def _read_image_file(
        cls, file_path: str, **reader_kwargs
    ) -> Tuple[bool, List[np.ndarray]]:
        """Reads image from a single file

        Generic reader method for reading a single
        image file from a local or S3 path. Determines
        the correct reader method to use based on the
        filepath's suffix.

        Params:
            file_path (str): Local or s3 filepath to image
            **reader_kwargs: Optional keyword arguments to pass onto
                specific reader methods e.g. `_read_tif`

        Returns:
            Tuple[bool, List[ndarray]]: Tuple where
                first entry specifies whether the result
                is a multipage image, and the second the
                list of images returned
        """
        fp_ext = Path(file_path).suffix
        if fp_ext in cls.multi_page_formats:
            fp_ext_str = fp_ext.replace(".", "")
            multi_page_reader = getattr(cls, f"_read_{fp_ext_str}")
            return_val = multi_page_reader(file_path, **reader_kwargs)

        else:
            img = cls._read_default(file_path, **reader_kwargs)
            return_val = (False, [img])

        return return_val

    @classmethod
    def _read_image_directory(
        cls,
        file_dir: str,
        valid_suffix: Optional[Union[str, List[str], None]] = None,
        **reader_kwargs,
    ) -> Tuple[bool, List[np.ndarray]]:
        """Reads a directory of image files

        Generic reader method for reading a set of images
        located in an S3 or local directory.

        Params:
            file_dir (str): Local or s3 directory path
            valid_suffix (Optional[Union[str, List[str], None]]):
                List of valid image suffixes - reader will only read
                files in the directory with a matching suffix
            **reader_kwargs: Optional keyword arguments to pass onto
                specific reader methods e.g. `_read_tif`

        Returns:
            Tuple[bool, List[ndarray]]: Tuple where
                first entry specifies whether the result
                is a multipage image, and the second the
                list of images returned
        """
        file_dir = file_dir if file_dir.endswith("/") else file_dir + "/"

        if file_dir.startswith("s3://"):
            img_fps = wr.s3.list_objects(file_dir)

        else:
            img_fps = glob(file_dir + "*")

        if valid_suffix is not None:
            valid_suffix = (
                valid_suffix if isinstance(valid_suffix, list) else [valid_suffix]
            )

            img_fps = [fp for fp in img_fps if Path(fp).suffix in valid_suffix]

        imgs_and_mp = [
            ImageReader._read_image_file(fp, **reader_kwargs) for fp in img_fps
        ]

        imgs = [imgs for _, imgs in imgs_and_mp]

        imgs_flattened = [img for imgs_list in imgs for img in imgs_list]

        if len(imgs_flattened) == 1:
            return_val = (False, imgs_flattened)
        else:
            return_val = (True, imgs_flattened)

        return return_val

    @classmethod
    def read(
        cls,
        file_path_or_dir: str,
        valid_suffix: Optional[Union[str, List[str], None]] = None,
        **reader_kwargs,
    ) -> Tuple[bool, List[np.ndarray]]:
        """Reads an image file or directory

        Reads an image file or directory either locally
        or stored in AWS S3.

        Params:
            file_path_or_dir (str): Local or s3 directory path
            valid_suffix (Optional[Union[str, List[str], None]]):
                List of valid image suffixes - reader will only read
                files in a directory with a matching suffix
            **reader_kwargs: Optional keyword arguments to pass onto
                specific reader methods e.g. `_read_tif`

        Returns:
            Tuple[bool, List[ndarray]]: Tuple where
                first entry specifies whether the result
                is a multipage image, and the second the
                list of images returned
        """
        fp_ext = Path(file_path_or_dir).suffix
        if fp_ext == "":
            return_val = ImageReader._read_image_directory(
                file_path_or_dir, valid_suffix=valid_suffix, **reader_kwargs
            )
        else:
            return_val = ImageReader._read_image_file(file_path_or_dir, **reader_kwargs)

        return return_val

    @classmethod
    def convert_from_path(
        cls,
        path: str,
        output_folder: str,
        file_format: Optional[str] = ".ppm",
        writer_params: Optional[Union[List[str], None]] = None,
        **reader_kwargs,
    ):
        """Reads an image file or directory

        Reads an image file or directory either locally
        or stored in AWS S3 and stores each image as a
        seperate image file in a local directory.

        Params:
            path (str): Local or s3 directory path
            output_folder (str): Directory for storing written
                images
            file_format (Optional[str]): Output file format
                for written images
            writer_params (Optional[Union[List[str], None]]):
                Optional parameters to pass onto `cv2.imwrite`
            **reader_kwargs: Optional keyword arguments to pass onto
                specific reader methods e.g. `_read_tif`
        """
        _, images = cls.read(path, **reader_kwargs)
        for i, img in enumerate(images):
            image_path = os.path.join(output_folder, f"image_{i}{file_format}")
            cv2.imwrite(image_path, img, writer_params)
