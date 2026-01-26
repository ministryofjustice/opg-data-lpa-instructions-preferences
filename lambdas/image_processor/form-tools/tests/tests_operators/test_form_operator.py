import re
import pytest
import numpy as np


class TestFormOperator:
    DEFAULT_CONFIG_PATH = "tests/tests_operators/data/configs/valid_config.yml"

    @pytest.mark.parametrize(
        "config, expected",
        [
            ("tests/tests_operators/data/configs/invalid_config.yml", False),
            ("tests/tests_operators/data/configs/valid_config.yml", True),
            ("tests/tests_operators/data/configs/valid_config2.yml", True),
            ("tests/tests_operators/data/configs/valid_config3.yml", True),
        ],
    )
    def test_attributes(self, config, expected):
        from form_tools.form_operators.form_operator import FormOperator
        from form_tools.form_operators.form_page_operator import FormPageOperator
        from form_tools.form_operators.ocr_engines.base import BaseOcrEngine

        if expected:
            operator = FormOperator.create_from_config(config)
            page_operator = FormPageOperator.create_from_config(config)

            assert isinstance(operator.rotation_engine, BaseOcrEngine)
            assert isinstance(operator.text_extractrion_engine, BaseOcrEngine)
            assert operator.form_page_operator.dict() == page_operator.dict()
            assert operator.config.dict() == page_operator.config.dict()

        else:
            with pytest.raises(Exception):
                FormOperator.create_from_config(config)

    @pytest.mark.parametrize(
        "form_meta_directory, expected",
        [
            ("tests/tests_operators/data/configs", []),
            ("tests/tests_operators/data/form_metadata", ["testid", "test"]),
        ],
    )
    def test_form_meta_store(self, form_meta_directory, expected):
        from form_tools.form_operators.form_operator import FormOperator

        meta_store = FormOperator.form_meta_store(form_meta_directory)
        assert sorted(expected) == sorted([k for k in meta_store])

    @pytest.mark.parametrize(
        "form_meta_directory, image_text, expected",
        [
            ("tests/tests_operators/data/configs", [""], []),
            (
                "tests/tests_operators/data/form_metadata",
                [
                    "hello",
                    "this is my dummy form text",
                    "it should have a page with an identifier",
                    "and here it comes",
                    "the form2",
                ],
                ["testid", "test"],
            ),
            (
                "tests/tests_operators/data/form_metadata",
                [
                    "hello",
                    "this is my dummy form text",
                    "it should have a page with an identifier",
                    "but it doesn't have one",
                    "but here's a similar one for the form ",
                ],
                [],
            ),
        ],
    )
    def test_match_form_images_text_to_form_meta(
        self, form_meta_directory, image_text, expected
    ):
        from form_tools.form_operators.form_operator import FormOperator

        operator = FormOperator.create_from_config(self.DEFAULT_CONFIG_PATH)
        matching_meta_store = operator.match_form_images_text_to_form_meta(
            form_meta_directory, image_text
        )
        matching_ids = [k for k in matching_meta_store]
        assert sorted(expected) == sorted(matching_ids)

    @pytest.mark.parametrize(
        "images, expected_images, expected_text",
        [
            (
                [
                    "tests/tests_operators/data/images/original.png",
                    "tests/tests_operators/data/images/rotated90.png",
                ],
                [
                    "tests/tests_operators/data/images/original.png",
                    "tests/tests_operators/data/images/original.png",
                ],
                [
                    "Ministry\nof Justice\n",
                    "Ministry\nof Justice\n",
                ],
            )
        ],
    )
    def test_ocr_methods(self, images, expected_images, expected_text):
        from form_tools.utils.image_reader import ImageReader
        from form_tools.form_operators.form_operator import FormOperator

        operator = FormOperator.create_from_config(self.DEFAULT_CONFIG_PATH)

        imgs = []
        for p in images:
            _, new_imgs = ImageReader.read(p)
            imgs.extend(new_imgs)

        expected_imgs = []
        for p in expected_images:
            _, exp = ImageReader.read(p)
            expected_imgs.extend(exp)

        text = operator.form_images_to_text(rimgs)
        assert [re.search(p, t) is not None for p, t in zip(expected_text, text)]
