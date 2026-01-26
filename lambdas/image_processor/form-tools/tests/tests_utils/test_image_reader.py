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

    def test_read_local_image_directory(self):
        old_environ = dict(os.environ)
        os.environ.update(self.TEMP_ENV_VARS)

        image_pathlib_path = Path(self.IMAGE_DIRECTORY)
        files = sorted([p for p in image_pathlib_path.glob("*.*")], reverse=True)
        array_files = sorted(
            [p for p in image_pathlib_path.glob("*.npy")], reverse=True
        )

        image_path = self.IMAGE_DIRECTORY
        ir = self.setup_test()
        mp, imgs = ir.read(image_path, valid_suffix=self.IMAGE_DIRECTORY_EXT)

        expected = [np.load(p) for p in array_files]
        zipped_values = zip(imgs, expected)

        assert mp
        assert all([np.array_equal(imgs, exp) for imgs, exp in zipped_values])

        os.environ.clear()
        os.environ.update(old_environ)

    def test_read_pdf(self):
        ir = self.setup_test()
        file = Path(self.PDF_IMAGE_PATH)

        image_path = self.PDF_IMAGE_PATH

        mp, imgs = ir.read(image_path)

        assert mp
        assert len(imgs) == 2
        assert all([isinstance(img, np.ndarray) for img in imgs])

        mp1, imgs1 = ir.read(
            self.PDF_IMAGE_PATH, conversion_parameters={"first_page": 1, "last_page": 1}
        )

        assert not mp1
        assert len(imgs1) == 1
        assert isinstance(imgs1[0], np.ndarray)

    def test_read_tif(self):
        ir = self.setup_test()
        file = Path(self.TIFF_IMAGE_PATH)

        image_path = self.PDF_IMAGE_PATH

        mp, imgs = ir.read(image_path)

        assert mp
        assert len(imgs) == 2
        assert all([isinstance(img, np.ndarray) for img in imgs])

    def test_convert_from_path(self):
        ir = self.setup_test()
        with TemporaryDirectory() as tmpdir:
            _ = ir.convert_from_path(
                self.PDF_IMAGE_PATH,
                output_folder=tmpdir,
            )
            image_files = [Path(p).name for p in os.listdir(tmpdir)]
            assert set([f"image_{i}.ppm" for i in range(2)]) == set(image_files)
