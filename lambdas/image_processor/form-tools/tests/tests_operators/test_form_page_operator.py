import os
import re
import cv2
import pytest
import numpy as np

from pydantic import ValidationError
from skimage.metrics import structural_similarity


class TestFormPageOperator:
    ATTRIBUTES_PASSED_FROM_CONFIG = [
        "knn",
        "proportion",
        "preprocessing_transforms",
        "homography_options",
    ]
    STRUCTURAL_SIMILARITY_THRESHOLD = 0.95

    @pytest.mark.parametrize(
        "config, expected",
        [
            ("tests/tests_operators/data/configs/invalid_config.yml", False),
            ("tests/tests_operators/data/configs/valid_config.yml", True),
            (
                {
                    "detector": {
                        "name": "SIFT",
                    },
                    "matcher": {
                        "id": "FLANN",
                        "args": [{"algorithm": 1, "trees": 5}, {"check": 50}],
                    },
                    "knn": 2,
                    "proportion": 0.7,
                },
                True,
            ),
        ],
    )
    def test_create_from_config(self, config, expected):
        from form_tools.form_operators.form_page_operator import FormPageOperator

        if expected:
            operator = FormPageOperator.create_from_config(config)

            assert isinstance(operator.detector, cv2.ORB) or isinstance(
                operator.detector, cv2.SIFT
            )
            assert re.search("cv2\\..*Matcher", str(type(operator.matcher))) is not None

            for attribute in self.ATTRIBUTES_PASSED_FROM_CONFIG:
                assert getattr(operator, attribute) == getattr(
                    operator.config, attribute
                )

        else:
            with pytest.raises(ValidationError):
                _ = FormPageOperator.create_from_config(config)

    @pytest.mark.parametrize(
        "form_meta_path, page_number, ocr_text, expected",
        [
            ("tests/tests_operators/data/form_metadata/test.json", 1, "first", True),
            (
                "tests/tests_operators/data/form_metadata/test.json",
                2,
                "first_second",
                False,
            ),
        ],
    )
    def test_check_image_text_against_form_page(
        self, form_meta_path, page_number, ocr_text, expected
    ):
        from form_tools.form_operators.form_page_operator import FormPageOperator
        from form_tools.form_meta import FormMetadata

        meta = FormMetadata.from_json(form_meta_path)
        form_page = meta.form_page(page_number)

        assert (
            FormPageOperator.check_image_text_against_form_page(form_page, ocr_text)
            == expected
        )

    @pytest.mark.parametrize(
        (
            "config, form_meta_path, page_number, page_image_path, "
            "page_template_image_path, page_image_str, expected"
        ),
        [
            (
                "tests/tests_operators/data/configs/valid_config.yml",
                "tests/tests_operators/data/form_metadata/test.json",
                1,
                "tests/tests_operators/data/images/rotated15.png",
                "tests/tests_operators/data/images/original.png",
                "first",
                True,
            ),
            (
                "tests/tests_operators/data/configs/valid_config2.yml",
                "tests/tests_operators/data/form_metadata/test.json",
                1,
                "tests/tests_operators/data/images/rotated15.png",
                "tests/tests_operators/data/images/original.png",
                "first",
                True,
            ),
            (
                "tests/tests_operators/data/configs/valid_config3.yml",
                "tests/tests_operators/data/form_metadata/test.json",
                1,
                "tests/tests_operators/data/images/rotated15.png",
                "tests/tests_operators/data/images/original.png",
                "first",
                True,
            ),
            (
                "tests/tests_operators/data/configs/valid_config.yml",
                "tests/tests_operators/data/form_metadata/test.json",
                1,
                "tests/tests_operators/data/images/random_image.jpg",
                "tests/tests_operators/data/images/original.png",
                "first",
                False,
            ),
        ],
    )
    def test_alignment(
        self,
        config,
        form_meta_path,
        page_number,
        page_image_path,
        page_template_image_path,
        page_image_str,
        expected,
    ):
        old_environ = dict(os.environ)
        new_environ = {"PYTEST_TEST_ENV": "test", **old_environ}
        os.environ.update(new_environ)

        from form_tools.form_operators.form_page_operator import FormPageOperator
        from form_tools.form_meta import FormMetadata
        from form_tools.utils.image_reader import ImageReader
        from form_tools.form_operators.preprocessors import convert_img_to_grayscale

        _, page_images = ImageReader.read(page_image_path)
        _, page_template_images = ImageReader.read(page_template_image_path)

        page_image = convert_img_to_grayscale(page_images[0])
        page_template_image = convert_img_to_grayscale(page_template_images[0])

        meta = FormMetadata.from_json(form_meta_path)
        form_page = meta.form_page(page_number)

        operator = FormPageOperator.create_from_config(config)

        if expected:
            aligned_image = operator.align_image_to_template(
                form_page=form_page,
                page_image=page_image,
                page_image_str=page_image_str,
                page_template_image=page_template_image,
                debug=True,
            )
            assert aligned_image.shape == page_template_image.shape
            assert (
                round(
                    structural_similarity(
                        aligned_image,
                        page_template_image,
                    ),
                    2,
                )
                >= self.STRUCTURAL_SIMILARITY_THRESHOLD
            )

        else:
            with pytest.raises(
                RuntimeError, match="Failed to generate a valid homography matrix"
            ):
                aligned_image = operator.align_image_to_template(
                    form_page=form_page,
                    page_image=page_image,
                    page_image_str=page_image_str,
                    page_template_image=page_template_image,
                )

        os.environ.clear()
        os.environ.update(old_environ)
