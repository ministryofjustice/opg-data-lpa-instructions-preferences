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
                RuntimeError,
                match="valid homography matrix|inlier support|too little of the page|excessively distort",
            ):
                aligned_image = operator.align_image_to_template(
                    form_page=form_page,
                    page_image=page_image,
                    page_image_str=page_image_str,
                    page_template_image=page_template_image,
                )

        os.environ.clear()
        os.environ.update(old_environ)


@pytest.fixture
def alignment_operator():
    from form_tools.form_operators.form_page_operator import FormPageOperator

    return FormPageOperator.create_from_config(
        {"detector": {"name": "SIFT"}, "matcher": {"id": "BF"}}
    )


@pytest.mark.parametrize(
    "matrix, mask, source_scale, target_scale, error",
    [
        (None, None, 1, 1, "valid homography"),
        (np.full((3, 3), np.nan), np.ones((20, 1)), 1, 1, "valid homography"),
        (np.eye(3), np.zeros((20, 1)), 1, 1, "inlier support"),
        (np.eye(3), np.r_[np.ones((10, 1)), np.zeros((10, 1))], 1, 1, "inlier support"),
        (np.eye(3), np.ones((20, 1)), 0.01, 1, "too little"),
        (np.eye(3), np.ones((20, 1)), 1, 0.01, "too little"),
    ],
)
def test_homography_rejects_unsupported_alignment(
    alignment_operator, monkeypatch, matrix, mask, source_scale, target_scale, error
):
    points = [(x, y) for x in range(10, 100, 20) for y in range(10, 100, 25)]
    source = [cv2.KeyPoint(x * source_scale, y * source_scale, 1) for x, y in points]
    target = [cv2.KeyPoint(x * target_scale, y * target_scale, 1) for x, y in points]
    matches = [cv2.DMatch(i, i, 0) for i in range(len(points))]
    monkeypatch.setattr(cv2, "findHomography", lambda *a, **kw: (matrix, mask))

    with pytest.raises(RuntimeError, match=error):
        alignment_operator._find_homography(
            matches, source, target, (100, 100), (100, 100)
        )


def test_homography_rejects_low_inlier_ratio(alignment_operator, monkeypatch):
    points = [
        cv2.KeyPoint(float(i % 10) * 10, float(i // 10) * 10, 1) for i in range(100)
    ]
    matches = [cv2.DMatch(i, i, 0) for i in range(100)]
    mask = np.r_[np.ones((24, 1)), np.zeros((76, 1))]
    monkeypatch.setattr(cv2, "findHomography", lambda *a, **kw: (np.eye(3), mask))
    with pytest.raises(RuntimeError, match="inlier support"):
        alignment_operator._find_homography(
            matches, points, points, (100, 100), (100, 100)
        )


@pytest.mark.parametrize(
    "matrix",
    [
        np.diag([1e-6, 1e-6, 1]),
        np.array([[1, 10, 0], [0, 1, 0], [0, 0, 1]]),
        np.array([[-1, 0, 100], [0, 1, 0], [0, 0, 1]]),
        np.array([[1, 0, 10000], [0, 1, 0], [0, 0, 1]]),
        np.array([[1, 0, 0], [0, 1, 0], [-0.02, 0, 1]]),
        np.array([[1, 0, 0], [0, 1, 0], [-0.01, 0, 1]]),
    ],
)
def test_homography_rejects_corrupt_page_geometry(alignment_operator, matrix):
    assert alignment_operator.homography_options is None
    with pytest.raises(RuntimeError):
        alignment_operator._check_homography_geometry(matrix, (100, 100), (100, 100))


@pytest.mark.parametrize(
    "matrix, source_shape, target_shape",
    [
        (np.eye(3), (100, 100), (100, 100)),
        (np.diag([2, 2, 1]), (100, 100), (200, 200)),
        (np.array([[-1, 0, 100], [0, -1, 100], [0, 0, 1]]), (100, 100), (100, 100)),
        (-np.eye(3), (100, 100), (100, 100)),
    ],
)
def test_homography_accepts_valid_page_geometry(
    alignment_operator, matrix, source_shape, target_shape
):
    alignment_operator._check_homography_geometry(matrix, source_shape, target_shape)


def test_invalid_geometry_is_rejected_before_warping(alignment_operator, monkeypatch):
    image = np.full((100, 100, 3), 255, dtype=np.uint8)
    monkeypatch.setattr(
        type(alignment_operator),
        "_return_matches",
        lambda *a: [
            cv2.DMatch(i, i, 0) for i in range(alignment_operator.minimum_matches + 1)
        ],
    )
    monkeypatch.setattr(
        type(alignment_operator),
        "_find_homography",
        lambda *a: np.array([[1, 10, 0], [0, 1, 0], [0, 0, 1]], dtype=float),
    )

    def unexpected_warp(*args, **kwargs):
        pytest.fail("An invalid alignment must not be applied to the image")

    monkeypatch.setattr(cv2, "warpPerspective", unexpected_warp)
    with pytest.raises(RuntimeError, match="excessively distort"):
        alignment_operator.align_image_to_template(image, image)
