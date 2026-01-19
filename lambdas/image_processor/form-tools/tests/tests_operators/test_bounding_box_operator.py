import cv2
import pytest
import numpy as np

from PIL import Image

image_path = "tests/tests_operators/data/images/random_image.jpg"


@pytest.mark.parametrize(
    "v1, v2, h1, h2", [(0, 50, 25, 100), (2, 10, 12, 36), (0, 1, 0, 100)]
)
def test_bounding_box_operator(v1, v2, h1, h2):
    from .form_tools.form_operators.bounding_box_operator import (
        BoundingBoxOperator,
        BoundingBox,
    )
    from .form_tools.utils.image_reader import ImageReader

    cv_img = cv2.imread(image_path)
    pil_img = Image.open(image_path)

    expected_cropped_image = cv_img[v1:v2, h1:h2]

    bb = BoundingBox.from_tuple((v1, v2, h1, h2), bb_format="tblr")

    bb_bb = BoundingBoxOperator.crop_image_to_bb(
        image=cv_img,
        bounding_box=bb,
    )

    bb_cv = BoundingBoxOperator.crop_image_to_bb(
        image=cv_img, bounding_box=(v1, v2, h1, h2), bb_format="tblr"
    )

    bb_pil = BoundingBoxOperator.crop_image_to_bb(
        image=pil_img, bounding_box=(v1, v2, h1, h2), bb_format="tblr"
    )

    bb_pil_cv = ImageReader._convert_PIL_to_cv2(bb_pil)

    bb_images = [bb_bb, bb_cv, bb_pil_cv]

    assert all([np.array_equal(bb, expected_cropped_image) for bb in bb_images])

    with pytest.raises(TypeError):
        bb_pil = BoundingBoxOperator.crop_image_to_bb(
            image=None, bounding_box=(v1, v2, h1, h2), bb_format="tblr"
        )
