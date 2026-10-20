import os
import re
import cv2
import pytest
import numpy as np
from pathlib import Path
from shutil import which

from pydantic import ValidationError
from skimage.metrics import structural_similarity


class TestFormPageOperator:
    ATTRIBUTES_PASSED_FROM_CONFIG = [
        "knn",
        "proportion",
        "similarity_options",
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
                match="valid similarity transform|inlier support|too little of the page|excessively distort|allowed limit",
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
        (None, None, 1, 1, "valid similarity"),
        (np.full((2, 3), np.nan), np.ones((20, 1)), 1, 1, "valid similarity"),
        (np.eye(2, 3), np.zeros((20, 1)), 1, 1, "inlier support"),
        (
            np.eye(2, 3),
            np.r_[np.ones((10, 1)), np.zeros((10, 1))],
            1,
            1,
            "inlier support",
        ),
        (np.eye(2, 3), np.ones((20, 1)), 0.01, 1, "too little"),
        (np.eye(2, 3), np.ones((20, 1)), 1, 0.01, "too little"),
    ],
)
def test_similarity_rejects_unsupported_alignment(
    alignment_operator, monkeypatch, matrix, mask, source_scale, target_scale, error
):
    points = [(x, y) for x in range(10, 100, 20) for y in range(10, 100, 25)]
    source = [cv2.KeyPoint(x * source_scale, y * source_scale, 1) for x, y in points]
    target = [cv2.KeyPoint(x * target_scale, y * target_scale, 1) for x, y in points]
    matches = [cv2.DMatch(i, i, 0) for i in range(len(points))]
    monkeypatch.setattr(cv2, "estimateAffinePartial2D", lambda *a, **kw: (matrix, mask))

    with pytest.raises(RuntimeError, match=error):
        alignment_operator._find_similarity(
            matches, source, target, (100, 100), (100, 100)
        )


def test_similarity_rejects_low_inlier_ratio(alignment_operator, monkeypatch):
    points = [
        cv2.KeyPoint(float(i % 10) * 10, float(i // 10) * 10, 1) for i in range(100)
    ]
    matches = [cv2.DMatch(i, i, 0) for i in range(100)]
    mask = np.r_[np.ones((24, 1)), np.zeros((76, 1))]
    monkeypatch.setattr(
        cv2, "estimateAffinePartial2D", lambda *a, **kw: (np.eye(2, 3), mask)
    )
    with pytest.raises(RuntimeError, match="inlier support"):
        alignment_operator._find_similarity(
            matches, points, points, (100, 100), (100, 100)
        )


@pytest.mark.parametrize(
    "matrix",
    [
        np.array([[1e-6, 0, 0], [0, 1e-6, 0]]),
        np.array([[1, 10, 0], [0, 1, 0]]),
        np.array([[-1, 0, 100], [0, 1, 0]]),
        np.array([[1, 0, 10000], [0, 1, 0]]),
        np.array([[1, 0, 40], [0, 1, 0]]),
        np.array([[1, 0, 0], [0, 1.1, 0]]),
        cv2.getRotationMatrix2D((50, 50), 21, 1),
        cv2.getRotationMatrix2D((50, 50), 180, 1),
        np.array([[1, 0, 0], [0, 1, 0], [-0.02, 0, 1]]),
        np.array([[1, 0, 0], [0, 1, 0], [-0.01, 0, 1]]),
    ],
)
def test_similarity_rejects_corrupt_page_geometry(alignment_operator, matrix):
    with pytest.raises(RuntimeError):
        alignment_operator._check_similarity_geometry(matrix, (100, 100), (100, 100))


@pytest.mark.parametrize(
    "matrix, source_shape, target_shape",
    [
        (np.eye(2, 3), (100, 100), (100, 100)),
        (np.array([[2, 0, 0], [0, 2, 0]]), (100, 100), (200, 200)),
        (cv2.getRotationMatrix2D((50, 50), 15, 1), (100, 100), (100, 100)),
        (np.array([[1, 0, 5], [0, 1, -5]]), (100, 100), (100, 100)),
    ],
)
def test_similarity_accepts_valid_page_geometry(
    alignment_operator, matrix, source_shape, target_shape
):
    alignment_operator._check_similarity_geometry(matrix, source_shape, target_shape)


def test_invalid_geometry_is_rejected_before_warping(alignment_operator, monkeypatch):
    image = cv2.imread("tests/tests_operators/data/images/original.png")
    monkeypatch.setattr(
        type(alignment_operator),
        "_find_similarity",
        lambda *a: np.array([[1, 10, 0], [0, 1, 0]], dtype=float),
    )

    def unexpected_warp(*args, **kwargs):
        pytest.fail("An invalid alignment must not be applied to the image")

    monkeypatch.setattr(cv2, "warpAffine", unexpected_warp)
    with pytest.raises(RuntimeError, match="shear"):
        alignment_operator.align_image_to_template(image, image)


@pytest.mark.parametrize(
    "angle, scale, shift", [(0, 1, (0, 0)), (5, 0.9, (12, -8)), (-12, 1.05, (-10, 15))]
)
def test_similarity_recovers_field_coordinates(alignment_operator, angle, scale, shift):
    template = cv2.imread("tests/tests_operators/data/images/original.png")
    h, w = template.shape[:2]
    forward = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale)
    forward[:, 2] += shift
    image = cv2.warpAffine(template, forward, (w, h), borderValue=(255, 255, 255))
    detector = alignment_operator.detector
    source_kps, source_desc = detector.detectAndCompute(
        cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), None
    )
    target_kps, target_desc = detector.detectAndCompute(
        cv2.cvtColor(template, cv2.COLOR_BGR2GRAY), None
    )
    matches = alignment_operator._return_matches(source_desc, target_desc)
    matrix = alignment_operator._find_similarity(
        matches, source_kps, target_kps, image.shape, template.shape
    )
    alignment_operator._check_similarity_geometry(matrix, image.shape, template.shape)
    field_corners = np.float32([[[w * 0.3, h * 0.3]], [[w * 0.7, h * 0.7]]])
    recovered = cv2.transform(cv2.transform(field_corners, forward), matrix)
    assert np.max(np.linalg.norm(recovered - field_corners, axis=2)) < 1
    aligned = alignment_operator.align_image_to_template(image, template)
    crop = np.s_[int(h * 0.3) : int(h * 0.7), int(w * 0.3) : int(w * 0.7)]
    assert (
        structural_similarity(
            cv2.cvtColor(aligned[crop], cv2.COLOR_BGR2GRAY),
            cv2.cvtColor(template[crop], cv2.COLOR_BGR2GRAY),
        )
        > 0.9
    )


def test_blank_scan_reports_alignment_failure(alignment_operator):
    image = np.full((100, 100, 3), 255, dtype=np.uint8)
    with pytest.raises(RuntimeError, match="No image features"):
        alignment_operator.align_image_to_template(image, image)


def test_ratio_matching_skips_incomplete_neighbour_pairs(
    alignment_operator, monkeypatch
):
    first = cv2.DMatch(0, 0, 1)
    second = cv2.DMatch(0, 1, 2)

    class Matcher:
        def knnMatch(self, *args, **kwargs):
            return [[], [first], [first, second]]

    monkeypatch.setattr(
        type(alignment_operator), "matcher", property(lambda self: Matcher())
    )
    descriptors = np.zeros((2, 128), dtype=np.float32)
    assert alignment_operator._return_matches(descriptors, descriptors) == [first]


def test_similarity_rejects_excessive_residuals(alignment_operator, monkeypatch):
    points = [
        cv2.KeyPoint(float(x), float(y), 1)
        for x in range(10, 100, 20)
        for y in range(10, 100, 25)
    ]
    matches = [cv2.DMatch(i, i, 0) for i in range(len(points))]
    monkeypatch.setattr(
        cv2,
        "estimateAffinePartial2D",
        lambda *a, **kw: (
            np.array([[1.0, 0.0, 10.0], [0.0, 1.0, 0.0]]),
            np.ones((len(points), 1)),
        ),
    )
    with pytest.raises(RuntimeError, match="residuals"):
        alignment_operator._find_similarity(
            matches, points, points, (100, 100), (100, 100)
        )


@pytest.mark.parametrize(
    "options",
    [
        {"threshold": 0},
        {"threshold": float("nan")},
        {"max_rotation_degrees": 90},
        {"singular_matrix_threshold": 0.05},
    ],
)
def test_invalid_similarity_config_is_rejected(options):
    from form_tools.form_operators.operator_configs import SimilarityConfig

    with pytest.raises(ValidationError):
        SimilarityConfig(**options)


def test_legacy_homography_options_require_migration():
    from form_tools.form_operators.form_page_operator import FormPageOperator

    with pytest.raises(ValidationError, match="no longer supported"):
        FormPageOperator.create_from_config(
            {
                "detector": {"name": "SIFT"},
                "matcher": {"id": "BF"},
                "homography_options": {},
            }
        )


@pytest.mark.parametrize(
    "document, scan_page, template, template_page, valid",
    [
        ("LP1F-Scan.pdf", 10, "lp1f", 1, True),
        ("LP1F-Scan.tiff", 10, "lp1f", 1, True),
        ("7000-0004-2643_20250227131843.371062_LP1F.pdf", 8, "lp1f", 1, True),
        ("700000059449_20250320164301.311702_LPC.pdf", 2, "lpc", 1, True),
        ("700000059449_20250320164301.311702_LPC.pdf", 1, "lpc", 2, False),
        ("700000069315_20250401121101.243519_LPC.pdf", 6, "lpc", 1, True),
        ("700000069315_20250401121101.243519_LPC.pdf", 7, "lpc", 2, True),
    ],
)
def test_local_upload_alignment(
    tmp_path, document, scan_page, template, template_page, valid
):
    from PIL import Image
    from pdf2image import convert_from_path
    from form_tools.form_operators.form_page_operator import FormPageOperator

    root = next(
        (
            path
            for path in Path(__file__).resolve().parents
            if (path / "local-services").is_dir()
        ),
        None,
    )
    if root is None:
        pytest.skip("Local upload fixtures are not available")
    document_path = (
        root / "local-services/localstack-request-handler/s3-uploads" / document
    )
    if not document_path.exists() or which("pdftoppm") is None:
        pytest.skip("Local upload fixtures and poppler are required")
    if document_path.suffix == ".pdf":
        image = convert_from_path(
            document_path,
            first_page=scan_page,
            last_page=scan_page,
            fmt="jpeg",
            output_folder=str(tmp_path),
        )[0]
    else:
        image = Image.open(document_path)
        image.seek(scan_page - 1)
        image = image.convert("RGB")
    scan_path = tmp_path / "scan.jpg"
    image.save(scan_path, "JPEG")
    scanned = cv2.imread(str(scan_path))
    extraction = root / "lambdas/image_processor/extraction"
    target = cv2.imread(
        str(extraction / f"opg_images/{template}_images/page_{template_page}.ppm")
    )
    operator = FormPageOperator.create_from_config(str(extraction / "opg-config.yaml"))
    cv2.setRNGSeed(42)
    if valid:
        aligned = operator.align_image_to_template(scanned, target)
        assert aligned.shape == target.shape
    else:
        with pytest.raises(RuntimeError, match="inlier support"):
            operator.align_image_to_template(scanned, target)
