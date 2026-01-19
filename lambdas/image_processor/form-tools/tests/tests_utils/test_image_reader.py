import os
import boto3
import pytest
import numpy as np

from moto import mock_s3
from pathlib import Path
from tempfile import TemporaryDirectory


class TestImageReader:
    TEMP_ENV_VARS = {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",  # pragma: allowlist secret
        "AWS_SECURITY_TOKEN": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": "eu-west-1",
    }
    IMAGE_DIRECTORY = "tests/tests_utils/images/image_directory/"
    IMAGE_DIRECTORY_EXT = [".png", ".jpg"]
    PDF_IMAGE_PATH = "tests/tests_utils/images/random_images.pdf"
    TIFF_IMAGE_PATH = "tests/tests_utils/images/random_images.tif"

    def setup_test(self):
        from .form_tools.utils.image_reader import ImageReader

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

    @pytest.mark.parametrize(
        "image_path",
        [
            "tests/tests_utils/images/image_directory/random_image.png",
            "tests/tests_utils/images/image_directory/random_image.jpg",
        ],
    )
    @mock_s3
    def test_read_s3_image(self, image_path):
        old_environ = dict(os.environ)
        os.environ.update(self.TEMP_ENV_VARS)
        aws_region = self.TEMP_ENV_VARS.get("AWS_DEFAULT_REGION")

        image_pathlib_path = Path(image_path)

        s3_client = boto3.client("s3")

        s3_client.create_bucket(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": aws_region},
        )
        s3_client.upload_file(image_path, "test-bucket", image_pathlib_path.name)

        ir = self.setup_test()
        mp, imgs = ir.read(f"s3://test-bucket/{image_pathlib_path.name}")

        image_pathlib_path = Path(image_path)
        file_ext = image_pathlib_path.suffix.replace(".", "")
        array_path = os.path.join(
            image_pathlib_path.parent, f"{image_pathlib_path.stem}_{file_ext}_array.npy"
        )

        expected = np.load(array_path)
        assert not mp
        assert np.array_equal(imgs[0], expected)

        os.environ.clear()
        os.environ.update(old_environ)

    @pytest.mark.parametrize("s3", [True, False])
    @mock_s3
    def test_read_local_image_directory(self, s3):
        old_environ = dict(os.environ)
        os.environ.update(self.TEMP_ENV_VARS)

        image_pathlib_path = Path(self.IMAGE_DIRECTORY)
        files = sorted([p for p in image_pathlib_path.glob("*.*")], reverse=True)
        array_files = sorted(
            [p for p in image_pathlib_path.glob("*.npy")], reverse=True
        )

        if s3:
            aws_region = self.TEMP_ENV_VARS.get("AWS_DEFAULT_REGION")

            s3_client = boto3.client("s3")

            s3_client.create_bucket(
                Bucket="test-bucket",
                CreateBucketConfiguration={"LocationConstraint": aws_region},
            )
            for file in files:
                s3_client.upload_file(
                    file.as_posix(), "test-bucket", f"image_directory/{file.name}"
                )

        image_path = "s3://test-bucket/image_directory/" if s3 else self.IMAGE_DIRECTORY
        ir = self.setup_test()
        mp, imgs = ir.read(image_path, valid_suffix=self.IMAGE_DIRECTORY_EXT)

        expected = [np.load(p) for p in array_files]
        zipped_values = zip(imgs, expected)

        assert mp
        assert all([np.array_equal(imgs, exp) for imgs, exp in zipped_values])

        os.environ.clear()
        os.environ.update(old_environ)

    @pytest.mark.parametrize("s3", [True, False])
    @mock_s3
    def test_read_pdf(self, s3):
        ir = self.setup_test()
        file = Path(self.PDF_IMAGE_PATH)

        if s3:
            aws_region = self.TEMP_ENV_VARS.get("AWS_DEFAULT_REGION")

            s3_client = boto3.client("s3")

            s3_client.create_bucket(
                Bucket="test-bucket",
                CreateBucketConfiguration={"LocationConstraint": aws_region},
            )

            s3_client.upload_file(file.as_posix(), "test-bucket", file.name)

        image_path = f"s3://test-bucket/{file.name}" if s3 else self.PDF_IMAGE_PATH

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

    @pytest.mark.parametrize("s3", [True, False])
    @mock_s3
    def test_read_tif(self, s3):
        ir = self.setup_test()
        file = Path(self.TIFF_IMAGE_PATH)

        if s3:
            aws_region = self.TEMP_ENV_VARS.get("AWS_DEFAULT_REGION")

            s3_client = boto3.client("s3")

            s3_client.create_bucket(
                Bucket="test-bucket",
                CreateBucketConfiguration={"LocationConstraint": aws_region},
            )

            s3_client.upload_file(file.as_posix(), "test-bucket", file.name)

        image_path = f"s3://test-bucket/{file.name}" if s3 else self.PDF_IMAGE_PATH

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
