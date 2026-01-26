import os
import boto3
import pytest
import numpy as np

from pathlib import Path
from tempfile import TemporaryDirectory


class TestImageReader:
    IMAGE_DIRECTORY = "tests/tests_utils/images/image_directory/"
    IMAGE_DIRECTORY_EXT = [".png", ".jpg"]
    PDF_IMAGE_PATH = "tests/tests_utils/images/random_images.pdf"
    TIFF_IMAGE_PATH = "tests/tests_utils/images/random_images.tif"

    def setup_test(self):
        from form_tools.utils.image_reader import ImageReader

        return ImageReader

    @pytest.mark.parametrize(
        "image_path",
        [
            "tests/tests_utils/images/image_directory/random_image.png",
            "tests/tests_utils/images/image_directory/random_image.jpg",
        ],
    )
    def test_read_local_image(self, image_path):
        ir = self.setup_test()
        mp, imgs = ir.read(image_path)

        image_pathlib_path = Path(image_path)
        file_ext = image_pathlib_path.suffix.replace(".", "")
        array_path = os.path.join(
            image_pathlib_path.parent, f"{image_pathlib_path.stem}_{file_ext}_array.npy"
        )

        expected = np.load(array_path)
        assert not mp
        assert np.array_equal(imgs[0], expected)
