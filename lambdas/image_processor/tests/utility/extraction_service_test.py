from unittest.mock import MagicMock, Mock
import pytest
from app.utility.extraction_service import ExtractionService
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
    return {
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


def test_get_matching_continuation_items(
    extraction_service, form_operator, monkeypatch
):
    # Barcode match scenario

    # Create test data
    scan_locations = {
        "continuations": {
            "continuation_1": "path/to/image1",
            "continuation_2": "path/to/image2",
        }
    }
    form_meta_directory = "path/to/meta/directory"

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
            return_value={"image_page_map": {"1": ["numpy_image"]}, "meta_id": "lpc"}
        ),
    )

    # Set up mock for logger
    mock_logger_debug = Mock()
    monkeypatch.setattr("builtins.print", mock_logger_debug)

    # Call the function
    result = extraction_service.get_matching_continuation_items(
        scan_locations, form_meta_directory, form_operator
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
    assert result == expected

    # OCR match scenario
    monkeypatch.setattr(
        extraction_service,
        "find_matches_from_barcodes",
        MagicMock(return_value={"image_page_map": {}, "meta_id": ""}),
    )

    monkeypatch.setattr(
        extraction_service,
        "get_ocr_matches",
        MagicMock(
            return_value={"image_page_map": {"1": ["numpy_image2"]}, "meta_id": "lpc2"}
        ),
    )
    result = extraction_service.get_matching_continuation_items(
        scan_locations, form_meta_directory, form_operator
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
    assert result == expected


def test_extract_images(monkeypatch, extraction_service, form_operator):
    # Setup
    matched_items = {"image_page_map": {(0, 0): [0]}}
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
    mock_form_operator.preprocess_form_images.assert_called_once_with([None, None])
    mock_form_operator.auto_rotate_form_images.assert_called_once_with([None, None])


def test_get_ocr_matches(monkeypatch, form_operator, extraction_service):
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
        "match_first_form_image_text_to_form_meta",
        MagicMock(return_value=["meta1", "meta2"]),
    )
    monkeypatch.setattr(
        extraction_service,
        "mixed_mode_page_identifier",
        MagicMock(return_value={"image_page_map": {"1": ["numpyarray"]}}),
    )
    # call the get_ocr_matches function with mock inputs
    result = extraction_service.get_ocr_matches(
        ["img1", "img2"], form_operator, "/path/to/form/meta"
    )

    # assert that the form_images_to_text method was called with the correct input
    form_operator.form_images_to_text.assert_called_once_with(["img1", "img2"])
    # assert that the methods were called with the correct input
    extraction_service.double_image_size.assert_called_once_with(["img1", "img2"])
    extraction_service.match_first_form_image_text_to_form_meta.assert_called_once_with(
        "/path/to/form/meta", ["text1", "text2"], form_operator
    )
    extraction_service.mixed_mode_page_identifier.assert_called_once_with(
        ["text1", "text2"], ["meta1", "meta2"], ["img1", "img2"]
    )
    # assert that the function returned the correct output
    assert result == {"image_page_map": {"1": ["numpyarray"]}}


def test_find_matches_from_barcodes():
    pass


def test_double_image_size():
    pass


def test_match_first_form_image_text_to_form_meta():
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


def test_mixed_mode_page_identifier():
    pass


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
        mock_form_images_as_strings, mock_form_metastore
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


def test_get_meta_page_text():
    pass


def test_calculate_similarity_ratio():
    pass


def test_get_similarity_score():
    pass


def test_get_meta_id_to_use():
    pass


def test_get_matching_image_results():
    pass


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
