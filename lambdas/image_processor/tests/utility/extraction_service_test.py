from unittest.mock import MagicMock, Mock

import pytest
import cv2
from app.utility.extraction_service import (
    ExtractionService,
    MatchingMetaToImages,
    FilteredMetastore,
)
from app.utility.bucket_manager import ScanLocationStore, ScanLocation
from app.utility.custom_logging import LogMessageDetails
from form_tools.form_operators import FormOperator


@pytest.fixture
def extraction_service():
    info_msg = LogMessageDetails()
    return ExtractionService(
        extraction_folder_path="extraction",
        folder_name="9999",
        output_folder_path="/tmp/output",
        info_msg=info_msg,
    )


@pytest.fixture
def form_operator():
    extraction_folder_path = "extraction"
    return FormOperator.create_from_config(f"{extraction_folder_path}/opg-config.yaml")


class MockFormMeta:
    def __init__(self, form_pages):
        self.form_pages = form_pages


class MockFormPage:
    def __init__(self, barcode, page_number, page_text):
        self.additional_args = {"extra": {"barcode": barcode, "page_text": page_text}}
        self.page_number = page_number
        self.identifier = "(.*meta_page_1.*)"


@pytest.fixture
def mock_form_metastore():
    meta_object = {
        "meta_1": MockFormMeta(
            form_pages=[
                MockFormPage(page_number=1, barcode="", page_text="meta_page_1_text"),
                MockFormPage(page_number=2, barcode="", page_text="meta_page_2_text"),
            ]
        ),
        "meta_2": MockFormMeta(
            form_pages=[
                MockFormPage(page_number=1, barcode="", page_text="meta2_page_1_text"),
                MockFormPage(page_number=2, barcode="", page_text="meta2_page_2_text"),
            ]
        ),
    }
    filtered_metastore = FilteredMetastore(
        filtered_metastore=meta_object, filtered_continuation_metastore={}
    )
    return filtered_metastore


@pytest.fixture
def mock_form_metastore_single_match():
    meta_object = {
        "meta_1": MockFormMeta(
            form_pages=[
                MockFormPage(page_number=1, barcode="", page_text="meta_page_1_text"),
                MockFormPage(page_number=2, barcode="", page_text="meta_page_2_text"),
            ]
        )
    }
    filtered_metastore = FilteredMetastore(
        filtered_metastore=meta_object, filtered_continuation_metastore={}
    )
    return filtered_metastore


@pytest.fixture
def mock_form_metastore_barcode_single():
    meta_object = {
        "meta_1": MockFormMeta(
            form_pages=[
                MockFormPage(page_number=1, barcode="1H7", page_text="meta_page_1_text")
            ]
        )
    }
    filtered_metastore = FilteredMetastore(
        filtered_metastore=meta_object, filtered_continuation_metastore={}
    )
    return filtered_metastore


@pytest.fixture
def mock_form_metastore_barcode_multiple():
    meta_object = {
        "meta_1": MockFormMeta(
            form_pages=[
                MockFormPage(
                    page_number=1, barcode="1C2", page_text="meta_page_1_text"
                ),
                MockFormPage(
                    page_number=2, barcode="1C2", page_text="meta_page_2_text"
                ),
            ]
        )
    }
    filtered_metastore = FilteredMetastore(
        filtered_metastore=meta_object, filtered_continuation_metastore={}
    )
    return filtered_metastore


def test_get_matching_continuation_items(
    extraction_service, form_operator, monkeypatch
):
    # Barcode match scenario

    # Create test data

    s1 = ScanLocation(location="path/to/image1", template="LPC")
    s2 = ScanLocation(location="path/to/image2", template="LPC")
    sls = ScanLocationStore()
    sls.add_continuation("continuation_1", s1)
    sls.add_continuation("continuation_2", s2)

    meta_store = {"meta1": {"field1": "value1"}, "meta2": {"field2": "value2"}}

    # Set up mock for form_operator methods
    monkeypatch.setattr(
        extraction_service, "get_preprocessed_images", MagicMock(return_value=[])
    )
    monkeypatch.setattr(
        "form_tools.form_operators.FormOperator.form_meta_store",
        MagicMock(
            return_value={"meta1": {"field1": "value1"}, "meta2": {"field2": "value2"}}
        ),
    )
    monkeypatch.setattr(
        extraction_service,
        "find_matches_from_barcodes",
        MagicMock(
            return_value=MatchingMetaToImages(
                image_page_map={"1": ["numpy_image"]}, meta_id="lpc"
            )
        ),
    )

    # Set up mock for logger
    mock_logger_debug = Mock()
    monkeypatch.setattr("builtins.print", mock_logger_debug)

    # Call the function
    result = extraction_service.get_matching_continuation_items(
        sls, meta_store, form_operator
    )
    expected = {
        "continuation_1": {
            "match": {"image_page_map": {"1": ["numpy_image"]}, "meta_id": "lpc"},
            "scan_location": "path/to/image1",
        },
        "continuation_2": {
            "match": {"image_page_map": {"1": ["numpy_image"]}, "meta_id": "lpc"},
            "scan_location": "path/to/image2",
        },
    }
    # Assertions
    assert (
        extraction_service.get_preprocessed_images.call_count == 2
    )  # Called once for each scan location
    match1 = result.matching_items["continuation_1"].match
    match2 = result.matching_items["continuation_2"].match

    assert (
        match1.image_page_map == expected["continuation_1"]["match"]["image_page_map"]
    )
    assert match1.meta_id == expected["continuation_1"]["match"]["meta_id"]
    assert (
        result.matching_items["continuation_1"].scan_location
        == expected["continuation_1"]["scan_location"]
    )

    assert (
        match2.image_page_map == expected["continuation_2"]["match"]["image_page_map"]
    )
    assert match2.meta_id == expected["continuation_2"]["match"]["meta_id"]
    assert (
        result.matching_items["continuation_2"].scan_location
        == expected["continuation_2"]["scan_location"]
    )

    # OCR match scenario
    monkeypatch.setattr(
        extraction_service,
        "find_matches_from_barcodes",
        MagicMock(return_value=MatchingMetaToImages(image_page_map={}, meta_id="")),
    )

    monkeypatch.setattr(
        extraction_service,
        "get_ocr_matches",
        MagicMock(
            return_value=MatchingMetaToImages(
                image_page_map={"1": ["numpy_image2"]}, meta_id="lpc2"
            )
        ),
    )
    result = extraction_service.get_matching_continuation_items(
        sls, meta_store, form_operator
    )
    expected = {
        "continuation_1": {
            "match": {"image_page_map": {"1": ["numpy_image2"]}, "meta_id": "lpc2"},
            "scan_location": "path/to/image1",
        },
        "continuation_2": {
            "match": {"image_page_map": {"1": ["numpy_image2"]}, "meta_id": "lpc2"},
            "scan_location": "path/to/image2",
        },
    }
    match1 = result.matching_items["continuation_1"].match
    match2 = result.matching_items["continuation_2"].match

    assert (
        match1.image_page_map == expected["continuation_1"]["match"]["image_page_map"]
    )
    assert match1.meta_id == expected["continuation_1"]["match"]["meta_id"]
    assert (
        result.matching_items["continuation_1"].scan_location
        == expected["continuation_1"]["scan_location"]
    )

    assert (
        match2.image_page_map == expected["continuation_2"]["match"]["image_page_map"]
    )
    assert match2.meta_id == expected["continuation_2"]["match"]["meta_id"]
    assert (
        result.matching_items["continuation_2"].scan_location
        == expected["continuation_2"]["scan_location"]
    )


def test_extract_images(monkeypatch, extraction_service, form_operator):
    # Setup
    matched_items = MatchingMetaToImages(meta_id="meta_1", image_page_map={(0, 0): [0]})
    meta = {}
    meta_id = "test_meta_id"
    scan_path = "test_scan_path"
    pass_dir = "test_pass_dir"
    fail_dir = "test_fail_dir"
    run_timestamp = "test_timestamp"

    # Lightest possible assertions here...
    monkeypatch.setattr(
        "form_tools.form_operators.FormOperator.align_images_to_template",
        MagicMock(return_value=[]),
    )
    monkeypatch.setattr(
        "form_tools.form_operators.FormOperator.extract_fields",
        MagicMock(return_value=[]),
    )

    monkeypatch.setattr(
        "form_tools.form_operators.FormOperator._write_to_pass",
        MagicMock(return_value=[]),
    )

    monkeypatch.setattr(
        "form_tools.form_operators.FormOperator._copy_to_fail",
        MagicMock(return_value=[]),
    )

    # Call function and assert
    extraction_service.extract_images(
        matched_items,
        meta,
        meta_id,
        form_operator,
        scan_path,
        pass_dir,
        fail_dir,
        run_timestamp,
    )

    # Assert that methods were called
    assert form_operator.align_images_to_template.call_count == 1
    assert form_operator.extract_fields.call_count == 1
    assert form_operator._write_to_pass.call_count == 1
    assert (
        form_operator._copy_to_fail.call_count == 0
    )  # Should not be called since no error was raised


def test_get_preprocessed_images(monkeypatch, tmp_path, extraction_service):
    # Create a fake PDF with two pages
    pdf_path = tmp_path / "test.pdf"
    with pdf_path.open(mode="wb") as f:
        f.write(b"fake PDF")

    # Mock ImageReader.read to return a list of two images
    mock_image_reader = MagicMock()
    mock_image_reader.read.return_value = (None, [None, None])
    monkeypatch.setattr(
        "form_tools.utils.image_reader.ImageReader.read", mock_image_reader.read
    )

    # Mock the form operator methods
    mock_form_operator = MagicMock()
    mock_form_operator.preprocess_form_images.return_value = [None, None]
    mock_form_operator.auto_rotate_form_images.return_value = [None, None]
    monkeypatch.setattr(
        "form_tools.form_operators.FormOperator", lambda: mock_form_operator
    )

    # Call the function under test
    images = extraction_service.get_preprocessed_images(pdf_path, mock_form_operator)

    # Assert that the correct number of images were returned
    assert len(images) == 2

    # Assert that ImageReader.read was called with the correct arguments
    mock_image_reader.read.assert_called_once_with(pdf_path)

    # Assert that the form operator methods were called with the correct arguments
    mock_form_operator.auto_rotate_form_images.assert_called_once_with([None, None])


def test_get_ocr_matches(
    monkeypatch,
    form_operator,
    extraction_service,
    mock_form_metastore_single_match,
    mock_form_metastore,
):
    # mock the double_image_size and match_first_form_image_text_to_form_meta methods
    monkeypatch.setattr(
        extraction_service,
        "double_image_size",
        MagicMock(return_value=["img1", "img2"]),
    )
    monkeypatch.setattr(
        "form_tools.form_operators.FormOperator.form_images_to_text",
        MagicMock(return_value=["text1", "text2"]),
    )
    monkeypatch.setattr(
        extraction_service,
        "mixed_mode_page_identifier",
        MagicMock(
            return_value=[
                MatchingMetaToImages(
                    meta_id="meta_1", image_page_map={"1": ["numpyarray"]}
                )
            ]
        ),
    )
    # call the get_ocr_matches function with mock inputs
    result = extraction_service.get_ocr_matches(
        ["img1", "img2"], form_operator, mock_form_metastore, "/path/to/form/meta"
    )

    # assert that the form_images_to_text method was called with the correct input
    form_operator.form_images_to_text.assert_called_once_with(["img1", "img2"])
    # assert that the methods were called with the correct input
    extraction_service.mixed_mode_page_identifier.assert_called_once_with(
        form_images_as_strings=["text1", "text2"],
        form_metastore=mock_form_metastore.filtered_metastore,
        form_images=["img1", "img2"],
        inline_continuation=False,
    )
    # assert that the function returned the correct output
    assert result.image_page_map == {"1": ["numpyarray"]}


def test_find_matches_from_barcodes_no_match(
    extraction_service, mock_form_metastore_barcode_single, monkeypatch
):
    images = []
    image_path = "extraction/opg_images/hw114_images/page_1.ppm"
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    images.append(image)

    result = extraction_service.find_matches_from_barcodes(
        images, mock_form_metastore_barcode_single, None
    )

    assert isinstance(result, MatchingMetaToImages)
    assert result.meta_id == "meta_1"
    assert len(result.image_page_map) == 0


def test_find_matches_from_barcodes_single_match(
    extraction_service, mock_form_metastore_barcode_single, monkeypatch
):
    images = []
    image_path = "extraction/opg_images/lp1h_images/page_1.ppm"
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    images.append(image)

    result = extraction_service.find_matches_from_barcodes(
        images, mock_form_metastore_barcode_single, None
    )

    assert isinstance(result, MatchingMetaToImages)
    assert result.meta_id == "meta_1"
    assert len(result.image_page_map) == 1


def test_find_matches_from_barcodes_multiple_matches(
    extraction_service, mock_form_metastore_barcode_multiple, monkeypatch
):
    images = []
    image1 = cv2.imread(
        "extraction/opg_images/lpc_images/page_1.ppm", cv2.IMREAD_GRAYSCALE
    )
    image2 = cv2.imread(
        "extraction/opg_images/lpc_images/page_2.ppm", cv2.IMREAD_GRAYSCALE
    )
    images.append(image1)
    images.append(image2)

    result = extraction_service.find_matches_from_barcodes(
        images, mock_form_metastore_barcode_multiple, None
    )

    assert isinstance(result, MatchingMetaToImages)
    assert result.meta_id == "meta_1"
    assert len(result.image_page_map) == 2


def test_double_image_size():
    pass


def test_match_first_form_image_text_to_form_meta():
    # This is largely covered by form tool tests
    pass


def test_similarity_score(extraction_service):
    # Test case 1: Identical strings
    str1 = "The quick brown fox jumps over the lazy dog."
    str2 = "The quick brown fox jumps over the lazy dog."
    assert extraction_service.similarity_score(str1, str2) == 1.0

    # Test case 2: Completely different strings
    str1 = "Python is a programming language."
    str2 = "The quick brown fox jumps over the lazy dog."
    assert extraction_service.similarity_score(str1, str2) == 0.0

    # Test case 3: Partially similar strings
    str1 = "The quick brown fox jumps over the lazy dog."
    str2 = "The quick brown fox jumps over the lazy cat."
    score = extraction_service.similarity_score(str1, str2)
    assert 0.8 < score < 0.9

    # Test case 4: Case sensitivity
    str1 = "The quick brown fox jumps over the lazy dog."
    str2 = "the quick brown Fox jumps over the lazy dog."
    assert extraction_service.similarity_score(str1, str2) == 1.0

    # Test case 5: Punctuation and special characters
    str1 = "The quick brown fox jumps over the lazy dog!"
    str2 = "The quick brown fox jumps over the lazy dog."
    assert extraction_service.similarity_score(str1, str2) == 1.0


def test_mixed_mode_page_identifier(
    form_operator, extraction_service, monkeypatch, mock_form_metastore
):
    form_images_as_strings = ["recognized text from form images"]
    form_metastore = mock_form_metastore
    form_images = ["img_1", "img_2"]

    # Patch any necessary dependencies
    mock_create_scan_to_template_distances = MagicMock()
    mock_create_scan_to_template_distances.return_value = [
        {
            "meta": "hw114",
            "distance": 20,
            "scan_page_no": 1,
            "template_page_no": 1,
            "form_image_as_string": "",
            "meta_page_text": "",
        },
        {
            "meta": "pfa117",
            "distance": 80,
            "scan_page_no": 1,
            "template_page_no": 1,
            "form_image_as_string": "",
            "meta_page_text": "",
        },
    ]
    monkeypatch.setattr(
        extraction_service,
        "create_scan_to_template_distances",
        mock_create_scan_to_template_distances,
    )

    mock_get_similarity_score = MagicMock()
    mock_get_similarity_score.return_value = 0.74
    monkeypatch.setattr(
        extraction_service, "get_similarity_score", mock_get_similarity_score
    )

    results = extraction_service.mixed_mode_page_identifier(
        form_images_as_strings, form_metastore, form_images
    )

    # Assert the results
    assert results[0].meta_id == "pfa117"
    assert results[0].image_page_map == {1: ["img_1"]}


@pytest.fixture
def mock_form_images_as_strings():
    return ["meta_page_1_text", "meta_page_2_text"]


def test_create_scan_to_template_distances(
    monkeypatch, extraction_service, mock_form_images_as_strings, mock_form_metastore
):
    mock_get_meta_page_text = MagicMock()
    mock_get_meta_page_text.return_value = "meta_page_1_text"
    # Call the method with a valid UID
    monkeypatch.setattr(
        extraction_service, "get_meta_page_text", mock_get_meta_page_text
    )

    distances = extraction_service.create_scan_to_template_distances(
        mock_form_images_as_strings, mock_form_metastore.filtered_metastore
    )

    assert (
        len(distances) == 8
    )  # Expect 8 distances for 2 images and 2 metas each with 2 form pages

    # Test the first distance
    assert distances[0]["meta"] == "meta_1"
    assert distances[0]["distance"] == 100
    assert distances[0]["scan_page_no"] == 1
    assert distances[0]["template_page_no"] == 1
    assert distances[0]["form_image_as_string"] == "meta_page_1_text"
    assert distances[0]["meta_page_text"] == "meta_page_1_text"

    # Test the last distance
    assert distances[-1]["meta"] == "meta_2"
    assert distances[-1]["distance"] == 0
    assert distances[-1]["scan_page_no"] == 2
    assert distances[-1]["template_page_no"] == 2
    assert distances[-1]["form_image_as_string"] == "meta_page_2_text"
    assert distances[-1]["meta_page_text"] == "meta_page_1_text"


def test_get_meta_page_text(extraction_service):
    form_page = MockFormPage(page_number=1, barcode="", page_text="test_text.txt")
    expected_meta_page_text = "hello world\n"

    extraction_service.extraction_folder_path = "tests/extraction"
    # Call the method being tested
    meta_page_text = extraction_service.get_meta_page_text(form_page)

    # Assert the results
    assert meta_page_text == expected_meta_page_text


def test_calculate_similarity_ratio(extraction_service, monkeypatch):
    form_page = MockFormPage(page_number=1, barcode="", page_text="meta_page_1_text")
    form_image_as_string = "Expects meta_page_1 as regex"
    meta_page_text = "Expects meta_page_1 as regex"

    expected_ratio = 100

    # Call the method being tested
    ratio = extraction_service.calculate_similarity_ratio(
        form_page, form_image_as_string, meta_page_text
    )

    # Assert the results
    assert ratio == expected_ratio


def test_calculate_similarity_ratio_no_regex(extraction_service, monkeypatch):
    form_page = MockFormPage(page_number=1, barcode="", page_text="meta_page_1_text")
    form_image_as_string = "Form image as string"
    meta_page_text = "Form image as string"

    expected_ratio = 0  # Replace with the expected similarity ratio

    # Call the method being tested
    ratio = extraction_service.calculate_similarity_ratio(
        form_page, form_image_as_string, meta_page_text
    )

    # Assert the results
    assert ratio == expected_ratio


def test_get_similarity_score(extraction_service):
    sorted_sim_scores = [
        {
            "meta": "pfa117",
            "distance": 42,
            "scan_page_no": 1,
            "template_page_no": 1,
            "form_image_as_string": "full match meta_page_1",
            "meta_page_text": "full match meta_page_1",
        },
        {
            "meta": "hw114",
            "distance": 600,
            "scan_page_no": 1,
            "template_page_no": 1,
            "form_image_as_string": "no match",
            "meta_page_text": "no match at all",
        },
    ]
    expected = 1.0
    actual = extraction_service.get_similarity_score(sorted_sim_scores)

    assert actual == expected


def test_get_meta_id_to_use(extraction_service):
    sorted_sim_scores = [
        {
            "meta": "pfa117",
            "distance": 42,
            "scan_page_no": 1,
            "template_page_no": 1,
            "form_image_as_string": "full match meta_page_1",
            "meta_page_text": "full match meta_page_1",
        },
        {
            "meta": "hw114",
            "distance": 600,
            "scan_page_no": 1,
            "template_page_no": 1,
            "form_image_as_string": "no match",
            "meta_page_text": "no match at all",
        },
    ]

    meta_id = extraction_service.get_meta_id_to_use(sorted_sim_scores)
    expected_meta_id = "pfa117"

    assert meta_id == expected_meta_id


def test_get_matching_image_results(extraction_service):
    meta_id_to_use = "meta_1"
    similarity_score = 0.8
    sorted_scan_template_entities = [
        {"template_page_no": 1, "scan_page_no": 1, "meta": "meta_1"},
        {"template_page_no": 2, "scan_page_no": 2, "meta": "meta_1"},
        {"template_page_no": 3, "scan_page_no": 3, "meta": "meta_1"},
    ]
    form_images = ["image1", "image2", "image3"]

    expected_matching_image_results = MatchingMetaToImages(
        meta_id="meta_1", image_page_map={1: ["image1"], 2: ["image2"], 3: ["image3"]}
    )

    # Call the method being tested
    matching_image_results = extraction_service.get_matching_image_results(
        meta_id_to_use, similarity_score, sorted_scan_template_entities, form_images
    )

    # Assert the results
    assert matching_image_results.meta_id == expected_matching_image_results.meta_id
    assert (
        matching_image_results.image_page_map
        == expected_matching_image_results.image_page_map
    )


# def test_extract_instructions_and_preferences(extraction_service, monkeypatch):
#     """
#     Only the most basic test here as we are testing the nested functions
#     more thoroughly elsewhere - add more tests when time permits
#     """
#     temp_output = "/tmp/output"
#     extraction_folder_path = "extraction"
#     folder_name = "1234"
#     image_locations = {"scan": f"{extraction_folder_path}/test_image.jpg"}
#
#     run_iap_extraction_mock = MagicMock()
#     run_iap_extraction_mock.return_value = []
#
#     monkeypatch.setattr(extraction_service, "run_iap_extraction", run_iap_extraction_mock)
#
#     # list_files_mock = MagicMock()
#     # list_files_mock.return_value = [
#     #     f"{temp_output}/pass/{folder_name}/scan/meta=lp1h/field_name=instructions/image_instructions.jpg",
#     #     f"{temp_output}/pass/{folder_name}/scan/meta=lp1h/field_name=preferences/image_preferences.jpg",
#     # ]
#     #
#     # monkeypatch.setattr(extraction_service, "list_files", list_files_mock)
#
#     get_timestamp_as_str_mock = MagicMock()
#     get_timestamp_as_str_mock.return_value = folder_name
#
#     monkeypatch.setattr(
#         extraction_service, "get_timestamp_as_str", get_timestamp_as_str_mock
#     )
#
#     result = extraction_service.extract_instructions_and_preferences(image_locations)
#
#     # Assert the output is as expected
#     assert result == {
#         "instructions": f"{temp_output}/pass/{folder_name}/scan/meta=lp1h/field_name=instructions/image_instructions.jpg",
#         "preferences": f"{temp_output}/pass/{folder_name}/scan/meta=lp1h/field_name=preferences/image_preferences.jpg",
#     }
#
#     form_operator = FormOperator.create_from_config(
#         f"{extraction_folder_path}/opg-config.yaml"
#     )
#     # Assert that the mocked functions were called as expected
#     extraction_service.run_iap_extraction.assert_called_once_with(
#         scan_locations={"scan": image_locations["scan"]}, form_operator=form_operator
#     )
#     list_files_mock.assert_called_once_with(f"{temp_output}/pass/1234", ".jpg")
#
