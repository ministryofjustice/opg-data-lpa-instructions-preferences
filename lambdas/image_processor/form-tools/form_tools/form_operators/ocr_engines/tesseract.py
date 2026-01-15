import os
import numpy as np
import concurrent.futures

from math import ceil
from itertools import chain
from logging import getLogger
from tesserocr import PyTessBaseAPI, PSM
from typing import List, Dict, Tuple, Any, Optional, ByteString, Callable

from .base import BaseOcrEngine
from ...utils.converters import convert_cv2_to_bytes

logger = getLogger(__name__)


class TesseractOcrEngine(BaseOcrEngine):
    multithreading_arguments: Optional[Dict[str, Any]]

    @property
    def multithreading_dictionary(self):
        return (
            {}
            if self.multithreading_arguments is None
            else self.multithreading_arguments
        )

    @staticmethod
    def _future_exception_handler(future: concurrent.futures.Future):
        try:
            result = future.result()
        except Exception as exc:
            logger.exception("%r generated an exception: %s" % (result, exc))
            raise
        return result

    @staticmethod
    def _get_osd(
        api: PyTessBaseAPI, image_bytes: Tuple[ByteString, int, int, int, int]
    ):
        try:
            api.SetImageBytes(*image_bytes)
            osd_info = api.DetectOrientationScript()
            rotation, orient_conf, _, _ = tuple(osd_info.values())
            return rotation, orient_conf

        except Exception:
            logger.warning(
                "Failed to read image OSD. Cannot autorotate, so using raw image."
            )
            return None, None

    @staticmethod
    def _get_text(
        api: PyTessBaseAPI, image_bytes: Tuple[ByteString, int, int, int, int]
    ):
        api.SetImageBytes(*image_bytes)
        api.Recognize()
        text = api.GetUTF8Text()
        return text

    def _run_tesseract_on_image_block(
        self,
        block_number: int,
        image_block: List[Tuple[ByteString, int, int, int, int]],
        api_kwargs: Dict[str, Any],
        method: Callable,
    ):
        try:
            with PyTessBaseAPI(**api_kwargs) as api:
                api_return_values = [
                    method(api, image_bytes) for image_bytes in image_block
                ]

            return block_number, api_return_values

        except Exception as ex:
            logger.exception(f"Unable to apply OCR method to images: {ex}")
            raise ex

    def _run_tesseract_on_images(
        self, images: List[np.ndarray], api_kwargs: Dict[str, Any], method_name: str
    ):
        multithreading_kwargs = self.multithreading_dictionary
        processes = int(multithreading_kwargs.get("max_workers", os.cpu_count()))

        images_bytes = [convert_cv2_to_bytes(image) for image in images]
        n = ceil(len(images_bytes) / processes)
        image_blocks = [images_bytes[i : i + n] for i in range(0, len(images_bytes), n)]
        method = getattr(self, method_name)

        with concurrent.futures.ThreadPoolExecutor(**multithreading_kwargs) as executor:
            future_vals = [
                executor.submit(
                    self._run_tesseract_on_image_block,
                    i,
                    img_block,
                    api_kwargs,
                    method,
                )
                for i, img_block in enumerate(image_blocks)
            ]

            imgs_block_text = [
                self._future_exception_handler(future)
                for future in concurrent.futures.as_completed(future_vals)
            ]

        sorted_blocks = sorted(imgs_block_text, key=lambda x: x[0])
        blocks_only = [v[1] for v in sorted_blocks]
        return_vals = list(chain(*blocks_only))

        if len(return_vals) != len(images):
            raise ValueError("Unkown multithreading error")

        return return_vals

    def extract_text_from_images(self, images: List[np.ndarray]):
        return self._run_tesseract_on_images(
            images=images,
            api_kwargs={"psm": PSM.AUTO_OSD, "lang": "eng"},
            method_name="_get_text",
        )

    def auto_rotate_images(self, images: List[np.ndarray]):
        rotation_arguments = self._run_tesseract_on_images(
            images=images,
            api_kwargs={"psm": PSM.OSD_ONLY, "lang": "osd"},
            method_name="_get_osd",
        )
        return self._rotate_images(images, rotation_arguments)
