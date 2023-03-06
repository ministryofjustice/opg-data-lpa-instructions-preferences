import os
import boto3
import requests
import pytest
from unittest.mock import patch, Mock, MagicMock
from moto import mock_s3, mock_sqs
from app.handler import ImageProcessor
from form_tools.form_operators import FormOperator

test_uid = "700000005"
test_queue = "test-queue"
test_bucket = "test-bucket"
event = {'Records': [{'body': '{\"uid\": \"700000000005\"}'}]}


@pytest.fixture(autouse=True)
def setup_environment_variables():
    os.environ["SIRIUS_URL"] = "http://sirius-test"
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["TARGET_ENVIRONMENT"] = "target_testing"


@pytest.fixture
def image_processor():
    return ImageProcessor(event)


def test_init(image_processor):
    assert image_processor.environment == os.getenv('ENVIRONMENT')
    assert image_processor.sirius_url == os.getenv('SIRIUS_URL')
    assert image_processor.target_environment == os.getenv('TARGET_ENVIRONMENT')
    assert image_processor.event == event
    assert image_processor.sirius_bucket == f"opg-backoffice-datastore-{os.getenv('ENVIRONMENT')}"
    assert image_processor.iap_bucket == f"lpa-iap-{os.getenv('ENVIRONMENT')}"
    assert image_processor.uid == None


@patch('boto3.client')
def test_setup_s3_connection(mock_boto3, image_processor):
    image_processor.setup_s3_connection()
    if image_processor.environment == "local":
        mock_boto3.assert_called_with("s3", endpoint_url="http://localstack:4566", region_name="eu-west-1")
    else:
        mock_boto3.assert_called_with("s3", region_name="eu-west-1")


def test_add_blank_files_to_paths_with_no_match(image_processor):
    initial_paths = {"instructions": "some/path/instructions.jpg"}
    expected_paths = {
        "instructions": "some/path/instructions.jpg",
        "preferences": "extraction/blank.jpg",
        "continuation-instructions": "extraction/blank.jpg",
        "continuation-preferences": "extraction/blank.jpg",
    }

    paths = image_processor.add_blank_files_to_paths_with_no_match(initial_paths)

    assert paths == expected_paths


def test_get_uid_from_event(image_processor):
    assert image_processor.get_uid_from_event() == '700000000005'


@pytest.fixture
def mock_get():
    with patch('app.handler.requests.get') as mock_get:
        yield mock_get


def test_make_request_to_sirius_successful(mock_get):
    # Setup the mock response
    mock_response = MagicMock()
    mock_response.text = '{"key": "value"}'
    mock_get.return_value = mock_response

    # Call the method with a valid UID
    image_processor = ImageProcessor(event)
    response_dict = image_processor.make_request_to_sirius(test_uid)

    # Verify the response
    assert response_dict == {"key": "value"}


def test_make_request_to_sirius_exception(mock_get):
    # Setup the mock request exception
    mock_get.side_effect = requests.exceptions.RequestException("Test Exception")

    # Call the method with a valid UID
    image_processor = ImageProcessor(event)
    response_dict = image_processor.make_request_to_sirius(test_uid)

    # Verify the response
    assert response_dict == {"error": "error getting response from Sirius"}


def test_make_request_to_sirius_decode_exception(mock_get):
    # Setup the mock response
    mock_response = MagicMock()
    mock_response.text = 'Invalid JSON'
    mock_get.return_value = mock_response

    # Call the method with a valid UID
    image_processor = ImageProcessor(event)
    response_dict = image_processor.make_request_to_sirius(test_uid)

    # Verify the response
    assert response_dict == {"error": "error decoding response from Sirius"}


def test_extract_s3_file_path(image_processor):
    s3_path = "s3://my_bucket/my_scan.pdf"
    expected_result = {"bucket": "my_bucket", "file_path": "my_scan.pdf"}
    assert image_processor.extract_s3_file_path(s3_path) == expected_result

    s3_path = "s3://my_bucket/folder1/folder2/my_scan.pdf"
    expected_result = {"bucket": "my_bucket", "file_path": "folder1/folder2/my_scan.pdf"}
    assert image_processor.extract_s3_file_path(s3_path) == expected_result

    s3_path = "s3://my_bucket/"
    expected_result = {"bucket": "my_bucket", "file_path": ""}
    assert image_processor.extract_s3_file_path(s3_path) == expected_result


def test_download_scanned_images(image_processor, monkeypatch):
    # Define test data
    s3_urls_dict = {
        "lpaScan": {"location": "s3://my_bucket/my_scan.pdf"},
        "continuationSheetScan": {
            "location": [
                "s3://my_bucket/my_continuation_sheet1.pdf",
                "s3://my_bucket/my_continuation_sheet2.pdf"
            ]
        }
    }

    # Define mock objects
    mock_s3 = MagicMock()
    mock_download_file = MagicMock()
    mock_s3.download_file = mock_download_file
    monkeypatch.setattr(image_processor, "s3", mock_s3)

    # Run the function to test
    result = image_processor.download_scanned_images(s3_urls_dict)

    # Check that the expected S3 files were downloaded
    assert len(mock_download_file.mock_calls) == 3
    mock_download_file.assert_any_call("my_bucket", "my_scan.pdf", "extraction/my_scan.pdf")
    mock_download_file.assert_any_call("my_bucket", "my_continuation_sheet1.pdf", "extraction/my_continuation_sheet1.pdf")
    mock_download_file.assert_any_call("my_bucket", "my_continuation_sheet2.pdf", "extraction/my_continuation_sheet2.pdf")

    # Check that the function returned the expected file paths
    expected_result = {
        "scan": "extraction/my_scan.pdf",
        "continuation_1": "extraction/my_continuation_sheet1.pdf",
        "continuation_2": "extraction/my_continuation_sheet2.pdf",
    }
    assert result == expected_result


def test_extract_instructions_and_preferences(image_processor, monkeypatch):
    extraction_folder_path = "extraction"
    image_locations = {"scan": f"{extraction_folder_path}/test_image.jpg"}

    # Create a mock object for FormOperator
    mock_form_operator = Mock()
    # Set the return value of run_full_pipeline to None
    mock_form_operator.run_full_pipeline.return_value = None
    # Monkeypatch the FormOperator.create_from_config method to return the mock object
    monkeypatch.setattr(FormOperator, 'create_from_config', Mock(return_value=mock_form_operator))

    list_files_mock = MagicMock()
    list_files_mock.return_value = [
            f"{extraction_folder_path}/pass/1234/field_name=instructions/image_instructions.jpg",
            f"{extraction_folder_path}/pass/1234/field_name=preferences/image_preferences.jpg",
        ]

    monkeypatch.setattr(image_processor, "list_files", list_files_mock)

    get_timestamp_as_str_mock = MagicMock()
    get_timestamp_as_str_mock.return_value = '1234'

    monkeypatch.setattr(image_processor, "get_timestamp_as_str", get_timestamp_as_str_mock)

    result = image_processor.extract_instructions_and_preferences(image_locations)

    # Assert the output is as expected
    assert result == {
        "instructions": f"{extraction_folder_path}/pass/1234/field_name=instructions/image_instructions.jpg",
        "preferences": f"{extraction_folder_path}/pass/1234/field_name=preferences/image_preferences.jpg",
    }

    # Assert that the mocked functions were called as expected
    mock_form_operator.run_full_pipeline.assert_called_once_with(
        form_path=image_locations["scan"],
        pass_dir=f"{extraction_folder_path}/pass/1234",
        fail_dir=f"{extraction_folder_path}/fail/1234",
        form_meta_directory=f"{extraction_folder_path}/metadata",
    )
    list_files_mock.assert_called_once_with(
        f"{extraction_folder_path}/pass/1234", ".jpg"
    )


@mock_s3
def test_put_images_to_bucket(image_processor):
    s3 = boto3.client('s3', region_name='us-east-1')
    iap_bucket = 'my-test-bucket'
    uid = '700000000001'
    image_processor.s3 = s3
    image_processor.iap_bucket = iap_bucket
    image_processor.uid = uid
    s3.create_bucket(Bucket=iap_bucket)

    # Create a test file
    test_file_content = b'Test file content'
    test_file_key = 'testfile'
    test_file_path = f'/tmp/{test_file_key}.jpg'
    with open(test_file_path, 'wb') as f:
        f.write(test_file_content)

    # Call the method being tested
    path_selection = {test_file_key: test_file_path}
    image_processor.put_images_to_bucket(path_selection)

    # Check that the file was uploaded to S3
    response = s3.get_object(Bucket=iap_bucket, Key=f'iap-{uid}-{test_file_key}')
    assert response['Body'].read() == test_file_content
