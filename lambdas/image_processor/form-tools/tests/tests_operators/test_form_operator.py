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
        "config, page_image_paths, changed",
        [
            (
                "tests/tests_operators/data/configs/valid_config.yml",
                [
                    "tests/tests_operators/data/images/original.png",
                    "tests/tests_operators/data/images/rotated15.png",
                ],
                True,
            ),
            (
                "tests/tests_operators/data/configs/valid_config2.yml",
                [
                    "tests/tests_operators/data/images/original.png",
                    "tests/tests_operators/data/images/rotated15.png",
                ],
                False,
            ),
        ],
    )
    def test_preprocess_form_images(self, config, page_image_paths, changed):
        from form_tools.form_operators.form_operator import FormOperator
        from form_tools.utils.image_reader import ImageReader

        imgs = []
        for p in page_image_paths:
            _, new_imgs = ImageReader.read(p)
            imgs.extend(new_imgs)

        operator = FormOperator.create_from_config(config)
        new_imgs = operator.preprocess_form_images(imgs)

        assert len(new_imgs) == len(imgs)

        if changed:
            assert all(
                [not np.array_equal(im1, im2) for im1, im2 in zip(imgs, new_imgs)]
            )

        else:
            assert all([np.array_equal(im1, im2) for im1, im2 in zip(imgs, new_imgs)])

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

        rimgs = operator.auto_rotate_form_images(imgs)
        assert [np.array_equal(im1, im2) for im1, im2 in zip(rimgs, expected_imgs)]

        text = operator.form_images_to_text(rimgs)
        assert [re.search(p, t) is not None for p, t in zip(expected_text, text)]

    @pytest.mark.parametrize(
        "form_images_path, indexes, form_meta, form_images_as_strings, expected, error",
        [
            (
                ["tests/tests_operators/data/forms/form_with_id.pdf"],
                [[0, 1]],
                "tests/tests_operators/data/form_metadata/testid.json",
                ["the form1 first", "other"],
                {1: [0], 2: []},
                None,
            ),
            (
                ["tests/tests_operators/data/forms/form_with_id.pdf"],
                [[0, 1]],
                "tests/tests_operators/data/form_metadata/testid.json",
                ["the form1 other", "other"],
                None,
                None,
            ),
            (
                ["tests/tests_operators/data/forms/form_with_id.pdf"],
                [[0, 1]],
                "tests/tests_operators/data/form_metadata/testid.json",
                ["the form1 first", "second"],
                {1: [0], 2: [1]},
                None,
            ),
            (
                [
                    "tests/tests_operators/data/forms/form_with_id.pdf",
                    "tests/tests_operators/data/forms/form_with_id.pdf",
                ],
                [[0, 1], [1]],
                "tests/tests_operators/data/form_metadata/testid.json",
                ["first", "the form1 second", "second"],
                {1: [0], 2: [1, 2]},
                "^No image matches required form page:",
            ),
            (
                ["tests/tests_operators/data/forms/form_with_id.pdf"],
                [[0, 1]],
                "tests/tests_operators/data/form_metadata/testid.json",
                None,
                {1: [0], 2: [1]},
                None,
            ),
            (
                ["tests/tests_operators/data/forms/form_with_id.pdf"],
                [[0, 1]],
                "tests/tests_operators/data/form_metadata/testid.json",
                None,
                {1: [0], 2: [1]},
                None,
            ),
            (
                [
                    "tests/tests_operators/data/forms/form_with_id.pdf",
                    "tests/tests_operators/data/forms/form_with_id.pdf",
                ],
                [[0, 1], [1]],
                "tests/tests_operators/data/form_metadata/testid.json",
                None,
                {1: [0], 2: [1, 2]},
                None,
            ),
        ],
    )
    def test_validate_and_match_pages(
        self,
        form_images_path,
        indexes,
        form_meta,
        form_images_as_strings,
        expected,
        error,
    ):
        from form_tools.utils.image_reader import ImageReader
        from form_tools.form_operators.form_operator import FormOperator
        from form_tools.form_meta.form_meta import FormMetadata

        meta = FormMetadata.from_json(form_meta)

        all_images = []
        for path, img_indexes in zip(form_images_path, indexes):
            _, imgs = ImageReader.read(path)
            all_images += [imgs[i] for i in img_indexes]

        form_operator = FormOperator.create_from_config(self.DEFAULT_CONFIG_PATH)

        if error is None and expected is not None:
            matched_pages = form_operator.validate_and_match_pages(
                all_images, meta, form_images_as_strings
            )

            full_expected = {
                p: [all_images[i] for i in exp_index]
                for p, exp_index in expected.items()
            }

            assert full_expected == matched_pages

        else:
            error_kwargs = {} if error is None else {"match": error}
            with pytest.raises(ValueError, **error_kwargs):
                form_operator.validate_and_match_pages(
                    all_images, meta, form_images_as_strings
                )
