from typing import Dict, List, Tuple, Union

from numpy import ndarray
from PIL import Image

from ..form_meta.bounding_box import BoundingBox


class BoundingBoxOperator:
    """Performs operations using a `BoundingBox`

    Class to perform operations on an image using
    a `BoundingBox`, or an object that can be
    converted to a `BoundingBox`. The main operation
    supported is cropping an image using the `BoundingBox`
    coordinates.
    """

    def __repr__(self):
        return "Bounding Box Operator"

    @staticmethod
    def _convert_object_to_bb(
        bb_object: Union[
            BoundingBox, Dict[str, int], Tuple[int, int, int, int], List[int]
        ],
        **bb_conversion_args
    ) -> BoundingBox:
        """Helper to convert object to `BoundingBox`

        Takes a candidate `BoundingBox` object and
        converts it to a `BoundingBox` class, if it
        isn't already an instance of one.

        Params:
            bb_object (Union[BoundingBox, Dict[str, int], Tuple[int, int, int, int], List[int]]):
                Candidate `BoundingBox` object
            **bb_conversion_args: Arguments to
                pass to `BoundingBox.from_infer`

        Returns:
            (BoundingBox): BoundingBox instance
        """  # noqa: E501
        if isinstance(bb_object, BoundingBox):
            return bb_object
        else:
            return BoundingBox.from_infer(bb_object, **bb_conversion_args)

    @classmethod
    def _crop_image_to_bb_ndarray(
        cls,
        image: ndarray,
        bounding_box: Union[
            BoundingBox, Dict[str, int], Tuple[int, int, int, int], List[int]
        ],
        **bb_conversion_args
    ) -> ndarray:
        """Helper to crop opencv image

        Takes a candidate `BoundingBox` object and
        uses it to crop a given opencv image.

        Params:
            image (ndarray): opencv image to crop
            bounding_box (Union[BoundingBox, Dict[str, int], Tuple[int, int, int, int], List[int]]):
                Candidate `BoundingBox` object
            **bb_conversion_args: Arguments to pass
                to `BoundingBox.from_infer`

        Returns:
            (ndarray): Cropped image
        """  # noqa: E501
        bb = cls._convert_object_to_bb(bounding_box, **bb_conversion_args)
        l, t, w, h = bb.to_tuple(bb_format="ltwh")
        return image[t : t + h, l : l + w]

    @classmethod
    def _crop_image_to_bb_pil(
        cls,
        image: Image,
        bounding_box: Union[
            BoundingBox, Dict[str, int], Tuple[int, int, int, int], List[int]
        ],
        **bb_conversion_args
    ) -> Image:
        """Helper to crop PIL image

        Takes a candidate `BoundingBox` object and
        uses it to crop a given PIL image.

        Params:
            image (Image): PIL image to crop
            bounding_box (Union[BoundingBox, Dict[str, int], Tuple[int, int, int, int], List[int]]):
                Candidate `BoundingBox` object
            **bb_conversion_args: Arguments to pass
                to `BoundingBox.from_infer`

        Returns:
            (Image): Cropped image
        """  # noqa: E501
        bb = cls._convert_object_to_bb(bounding_box, **bb_conversion_args)
        bb_tuple = bb.to_tuple(bb_format="ltrb")
        bb_image = image.crop(bb_tuple)
        return bb_image

    @classmethod
    def crop_image_to_bb(
        cls,
        image: Union[object, ndarray],
        bounding_box: Union[
            BoundingBox, Dict[str, int], Tuple[int, int, int, int], List[int]
        ],
        **bb_conversion_args
    ) -> Union[object, ndarray]:
        """Crops image to bounding box coordinates

        Takes a candidate `BoundingBox` object and
        uses it to crop a PIL or opencv image to
        the specified region.

        Params:
            image (Union[Image, ndarray]): PIL or opencv image to crop
            bounding_box (Union[BoundingBox, Dict[str, int], Tuple[int, int, int, int], List[int]]):
                Candidate `BoundingBox` object
            **bb_conversion_args: Arguments to pass
                to `BoundingBox.from_infer`

        Returns:
            (Image): Cropped image
        """  # noqa: E501
        image_type = str(type(image))
        if "PIL" in image_type:
            bb_image = cls._crop_image_to_bb_pil(
                image, bounding_box, **bb_conversion_args
            )
        elif "ndarray" in image_type:
            bb_image = cls._crop_image_to_bb_ndarray(
                image, bounding_box, **bb_conversion_args
            )
        else:
            raise TypeError(
                "Supplied image must be a numpy ndarray\n" "or a PIL image."
            )
        return bb_image
