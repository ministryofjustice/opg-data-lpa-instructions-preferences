import os
import boto3
import requests
import pytest
import jwt
import numpy as np
from unittest.mock import patch, Mock, MagicMock
from botocore.exceptions import ClientError
from moto import mock_secretsmanager, mock_s3
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
    os.environ["TARGET_ENVIRONMENT"] = "target-testing"
    os.environ["SESSION_DATA"] = 'ops@email.com'
    os.environ['SECRET_PREFIX'] = 'testing'


@pytest.fixture
def image_processor():
    return ImageProcessor(event)


def test_init_function(image_processor):
    assert image_processor.environment == os.getenv('ENVIRONMENT')
    assert image_processor.target_environment == os.getenv('TARGET_ENVIRONMENT')
    assert image_processor.secret_key_prefix == os.getenv('SECRET_PREFIX')
    assert image_processor.sirius_url == os.getenv('SIRIUS_URL')
    assert image_processor.sirius_url_part == os.getenv('SIRIUS_URL_PART')
    assert image_processor.event == event
    assert image_processor.s3 is not None
    assert image_processor.sirius_bucket == f'opg-backoffice-datastore-{os.getenv("TARGET_ENVIRONMENT")}'
    assert image_processor.iap_bucket == f'lpa-iap-{os.getenv("ENVIRONMENT")}'
    assert image_processor.extraction_folder_path == 'extraction'
    assert image_processor.output_folder_path == '/tmp/output'
    assert image_processor.folder_name == '9999'
    assert image_processor.continuation_instruction_count == 0
    assert image_processor.continuation_preference_count == 0
    assert image_processor.secret_manager is not None
    assert image_processor.uid is None


@patch('boto3.client')
def test_setup_s3_connection(mock_boto3, image_processor):
    image_processor.setup_s3_connection()
    if image_processor.environment == "local":
        mock_boto3.assert_called_with("s3", endpoint_url="http://localstack:4566", region_name="eu-west-1")
    else:
        mock_boto3.assert_called_with("s3", region_name="eu-west-1")


@mock_secretsmanager
def test_setup_secret_manager_connection(image_processor):
    sm = image_processor.setup_secret_manager_connection()

    # check that we can create a secret
    secret_name = 'test-secret'
    secret_value = 'my-secret-value'
    sm.create_secret(Name=secret_name, SecretString=secret_value)

    # check that we can retrieve the secret
    retrieved_secret = sm.get_secret_value(SecretId=secret_name)
    assert retrieved_secret['SecretString'] == secret_value


def test_get_uid_from_event(image_processor):
    assert image_processor.get_uid_from_event() == '700000000005'


@pytest.fixture
def mock_get():
    with patch('app.handler.requests.get') as mock_get:
        yield mock_get


def test_make_request_to_sirius_successful(mock_get, monkeypatch):
    # Setup the mock response
    mock_response = MagicMock()
    mock_response.text = '{"key": "value"}'
    mock_get.return_value = mock_response

    image_processor = ImageProcessor(event)
    mock_sirius_headers = MagicMock()
    mock_sirius_headers.return_value = {
        "Content-Type": 'application/json',
        "Authorization": "Bearer 1234"
    }
    # Call the method with a valid UID
    monkeypatch.setattr(image_processor, "build_sirius_headers", mock_sirius_headers)
    response_dict = image_processor.make_request_to_sirius(test_uid)

    # Verify the response
    assert response_dict == {"key": "value"}


def test_make_request_to_sirius_exception(mock_get, monkeypatch):
    # Setup the mock request exception
    mock_get.side_effect = requests.exceptions.RequestException("Test Exception")

    image_processor = ImageProcessor(event)
    mock_sirius_headers = MagicMock()
    mock_sirius_headers.return_value = {
        "Content-Type": 'application/json',
        "Authorization": "Bearer 1234"
    }
    monkeypatch.setattr(image_processor, "build_sirius_headers", mock_sirius_headers)
    # Call the method with a valid UID
    response_dict = image_processor.make_request_to_sirius(test_uid)

    # Verify the response
    assert response_dict == {"error": "Error getting response from Sirius"}


def test_make_request_to_sirius_decode_exception(mock_get, monkeypatch):
    # Setup the mock response
    mock_response = MagicMock()
    mock_response.text = 'Invalid JSON'
    mock_get.return_value = mock_response

    # Call the method with a valid UID
    image_processor = ImageProcessor(event)

    mock_sirius_headers = MagicMock()
    mock_sirius_headers.return_value = {
        "Content-Type": 'application/json',
        "Authorization": "Bearer 1234"
    }
    monkeypatch.setattr(image_processor, "build_sirius_headers", mock_sirius_headers)

    response_dict = image_processor.make_request_to_sirius(test_uid)

    # Verify the response
    assert response_dict == {"error": "Error decoding response from Sirius"}


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
    mock_download_file.assert_any_call("my_bucket", "my_scan.pdf", "/tmp/output/my_scan.pdf")
    mock_download_file.assert_any_call("my_bucket", "my_continuation_sheet1.pdf",
                                       "/tmp/output/my_continuation_sheet1.pdf")
    mock_download_file.assert_any_call("my_bucket", "my_continuation_sheet2.pdf",
                                       "/tmp/output/my_continuation_sheet2.pdf")

    # Check that the function returned the expected file paths
    expected_result = {
        "scan": "/tmp/output/my_scan.pdf",
        "continuation_1": "/tmp/output/my_continuation_sheet1.pdf",
        "continuation_2": "/tmp/output/my_continuation_sheet2.pdf",
    }
    assert result == expected_result


def test_extract_instructions_and_preferences(image_processor, monkeypatch):
    """
    Only the most basic test here as we are testing the nested functions
    more thoroughly elsewhere - add more tests when time permits
    """
    temp_output = "/tmp/output"
    extraction_folder_path = 'extraction'
    folder_name = '1234'
    image_locations = {"scan": f"{extraction_folder_path}/test_image.jpg"}

    run_iap_extraction_mock = MagicMock()
    run_iap_extraction_mock.return_value = None

    monkeypatch.setattr(image_processor, "run_iap_extraction", run_iap_extraction_mock)

    list_files_mock = MagicMock()
    list_files_mock.return_value = [
        f"{temp_output}/pass/{folder_name}/scan/meta=lp1h/field_name=instructions/image_instructions.jpg",
        f"{temp_output}/pass/{folder_name}/scan/meta=lp1h/field_name=preferences/image_preferences.jpg",
    ]

    monkeypatch.setattr(image_processor, "list_files", list_files_mock)

    get_timestamp_as_str_mock = MagicMock()
    get_timestamp_as_str_mock.return_value = folder_name

    monkeypatch.setattr(image_processor, "get_timestamp_as_str", get_timestamp_as_str_mock)

    result = image_processor.extract_instructions_and_preferences(image_locations)

    # Assert the output is as expected
    assert result == {
        "instructions": f"{temp_output}/pass/{folder_name}/scan/meta=lp1h/field_name=instructions/image_instructions.jpg",
        "preferences": f"{temp_output}/pass/{folder_name}/scan/meta=lp1h/field_name=preferences/image_preferences.jpg",
    }

    form_operator = FormOperator.create_from_config(f"{extraction_folder_path}/opg-config.yaml")
    # Assert that the mocked functions were called as expected
    image_processor.run_iap_extraction.assert_called_once_with(
        form_path=image_locations["scan"],
        pass_dir=f"{temp_output}/pass/{folder_name}/scan",
        fail_dir=f"{temp_output}/fail/{folder_name}/scan",
        form_meta_directory=f"{extraction_folder_path}/metadata",
        form_operator=form_operator
    )
    list_files_mock.assert_called_once_with(
        f"{temp_output}/pass/1234", ".jpg"
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
    head = s3.head_object(Bucket=iap_bucket, Key=f'iap-{uid}-{test_file_key}')
    assert head['Metadata'] == {
        "continuationsheetsinstructions": "0",
        "continuationsheetspreferences": "0"
    }


def test_find_instruction_and_preference_paths(image_processor, monkeypatch):
    # Test case where both instructions and preferences files are found
    path_selection = {"instructions": "", "preferences": ""}
    paths = [
        "/path/to/instructions/meta=lp1f/field_name=instructions/",
        "/path/to/preferences/meta=lp1f/field_name=preferences/"
    ]
    result = image_processor.find_instruction_and_preference_paths(path_selection, paths)
    assert result["path_selection"]["instructions"] == "/path/to/instructions/meta=lp1f/field_name=instructions/"
    assert result["path_selection"]["preferences"] == "/path/to/preferences/meta=lp1f/field_name=preferences/"
    assert result["continuation_instructions"] == False
    assert result["continuation_preferences"] == False

    # Test case for continuation sheets
    paths = [
        "/path/to/instructions/meta=lp1h/field_name=instructions/",
        "/path/to/preferences/meta=lp1h/field_name=preferences/",
        "/path/to/instructions/meta=lp1h/field_name=continuation_checkbox_instructions",
        "/path/to/preferences/meta=lp1h/field_name=continuation_checkbox_preferences"
    ]
    detect_marked_checkbox_mock = MagicMock()
    detect_marked_checkbox_mock.return_value = True

    monkeypatch.setattr(image_processor, "detect_marked_checkbox", detect_marked_checkbox_mock)
    result = image_processor.find_instruction_and_preference_paths(path_selection, paths)
    assert result["path_selection"]["instructions"] == "/path/to/instructions/meta=lp1h/field_name=instructions/"
    assert result["path_selection"]["preferences"] == "/path/to/preferences/meta=lp1h/field_name=preferences/"
    assert result["continuation_instructions"] == True
    assert result["continuation_preferences"] == True


def test_get_continuation_sheet_paths(image_processor, monkeypatch):
    continuation_sheet_type = 'BOTH'
    path_filter = 'continuation_2'

    def mock_detect_marked_checkbox(path):
        if 'preferences_checkbox_p1' in path:
            return True
        elif 'instructions_checkbox_p2' in path:
            return True
        else:
            return False

    monkeypatch.setattr(image_processor, 'detect_marked_checkbox', mock_detect_marked_checkbox)

    # Test case for two paths that have marked checkboxes. Also check filter applies
    paths = [
        '/path/to/continuation_1/meta=lph1/field_name=preferences_checkbox_p1/a.jpg',
        '/path/to/continuation_1/meta=lpc/field_name=preferences_checkbox_p1/b.jpg',
        '/path/to/continuation_1/meta=lpc/field_name=instructions_checkbox_p2/c.jpg',
        '/path/to/continuation_1/meta=lpc/field_name=continuation_sheet_p1/a.jpg',
        '/path/to/continuation_1/meta=lpc/field_name=continuation_sheet_p2/b.jpg',
        '/path/to/continuation_2/meta=lph1/field_name=preferences_checkbox_p1/a.jpg',
        '/path/to/continuation_2/meta=lpc/field_name=preferences_checkbox_p1/b.jpg',
        '/path/to/continuation_2/meta=lpc/field_name=instructions_checkbox_p2/c.jpg',
        '/path/to/continuation_2/meta=lpc/field_name=continuation_sheet_p1/a.jpg',
        '/path/to/continuation_2/meta=lpc/field_name=continuation_sheet_p2/b.jpg'
    ]
    result = image_processor.get_continuation_sheet_paths(paths, continuation_sheet_type, path_filter)

    expected_result = {
        'p1': {
            'path': '/path/to/continuation_2/meta=lpc/field_name=continuation_sheet_p1/a.jpg',
            'type': 'preferences'
        },
        'p2': {
            'path': '/path/to/continuation_2/meta=lpc/field_name=continuation_sheet_p2/b.jpg',
            'type': 'instructions'
        }
    }

    assert result == expected_result

    # Test case for no detected checkboxes
    paths = [
        '/path/to/continuation_2/meta=lpc/field_name=continuation_sheet_p1/a.jpg',
        '/path/to/continuation_2/meta=lpc/field_name=continuation_sheet_p2/b.jpg'
    ]
    result = image_processor.get_continuation_sheet_paths(paths, continuation_sheet_type, path_filter)

    expected_result = {
        'p1': {
            'path': '/path/to/continuation_2/meta=lpc/field_name=continuation_sheet_p1/a.jpg',
            'type': 'neither'
        },
        'p2': {
            'path': '/path/to/continuation_2/meta=lpc/field_name=continuation_sheet_p2/b.jpg',
            'type': 'neither'
        }
    }
    assert result == expected_result


def test_get_continuation_sheet_type(image_processor):
    assert image_processor.get_continuation_sheet_type(True, True) == 'BOTH'
    assert image_processor.get_continuation_sheet_type(True, False) == 'INSTRUCTIONS'
    assert image_processor.get_continuation_sheet_type(False, True) == 'PREFERENCES'
    assert image_processor.get_continuation_sheet_type(False, False) == 'NEITHER'


def test_get_selected_paths_for_upload(image_processor):
    # Mock input parameters
    paths = [
        "/path/to/instructions/meta=lp1h/field_name=instructions/",
        "/path/to/preferences/meta=lp1h/field_name=preferences/",
        "/path/to/instructions/meta=lph/field_name=continuation_checkbox_instructions",
        "/path/to/preferences/meta=lph/field_name=continuation_checkbox_preferences",
        "/path/to/continuation_1/meta=lpc/field_name=preferences_checkbox_p1",
        "/path/to/continuation_1/meta=lpc/field_name=instructions_checkbox_p2",
        "/path/to/continuation_1/meta=lpc/field_name=continuation_sheet_p1",
        "/path/to/continuation_1/meta=lpc/field_name=continuation_sheet_p2"
    ]
    continuation_keys_to_use = ['continuation_1']

    # Mock objects
    mock_response = {
        'path_selection': {
            'instructions': "/path/to/instructions/meta=lp1h/field_name=instructions/",
            'preferences': "/path/to/preferences/meta=lp1h/field_name=preferences/"
        },
        'continuation_instructions': True,
        'continuation_preferences': False
    }
    mock_continuation_sheets = {
        'p1': {
            'path': '/path/to/continuation_1/meta=lpc/field_name=continuation_sheet_p1',
            'type': 'preferences'
        },
        'p2': {
            'path': '/path/to/continuation_1/meta=lpc/field_name=continuation_sheet_p2',
            'type': 'instructions'
        }
    }

    # Patch the mock methods
    with patch.object(image_processor, 'find_instruction_and_preference_paths', return_value=mock_response):
        with patch.object(image_processor, 'get_continuation_sheet_type', return_value='BOTH'):
            with patch.object(image_processor, 'get_continuation_sheet_paths', return_value=mock_continuation_sheets):
                # Call the method under test
                result = image_processor.get_selected_paths_for_upload(paths, continuation_keys_to_use)

    # Verify the expected output
    expected_result = {
        'instructions': '/path/to/instructions/meta=lp1h/field_name=instructions/',
        'preferences': '/path/to/preferences/meta=lp1h/field_name=preferences/',
        'continuation_instructions_1': '/path/to/continuation_1/meta=lpc/field_name=continuation_sheet_p2',
        'continuation_preferences_1': '/path/to/continuation_1/meta=lpc/field_name=continuation_sheet_p1'
    }
    assert result == expected_result


def test_update_continuation_sheet_counts(image_processor):
    paths_to_extracted_images = {
        'continuation_instructions_1': '/path/to/image1',
        'continuation_instructions_2': '/path/to/image2',
        'continuation_preferences_1': '/path/to/image3',
    }

    image_processor.update_continuation_sheet_counts(paths_to_extracted_images)

    assert image_processor.continuation_instruction_count == 2
    assert image_processor.continuation_preference_count == 1


def test_update_continuation_sheet_counts_with_no_continuation_sheets(image_processor):
    paths_to_extracted_images = {
        'some_other_sheet_1': '/path/to/image1',
        'some_other_sheet_2': '/path/to/image2',
    }

    image_processor.update_continuation_sheet_counts(paths_to_extracted_images)

    assert image_processor.continuation_instruction_count == 0
    assert image_processor.continuation_preference_count == 0


def test_merge_continuation_images_into_path_selection(image_processor):
    # Define inputs
    path_selection = {
        "preferences": "somepath/preferences",
        "instructions": "somepath/instructions"
    }
    continuation_sheets = {
        "continuation_1": {
            "p1": {
                "path": "somepath/continuation_1_preferences_p1",
                "type": "preferences"
            },
            "p2": {
                "path": "somepath/continuation_1_instructions_p2",
                "type": "instructions"
            }
        },
        "continuation_2": {
            "p1": {
                "path": "somepath/continuation_2_preferences_p1",
                "type": "preferences"
            },
            "p2": {
                "path": "somepath/continuation_2_random_p2",
                "type": "neither"
            }
        }
    }

    # Define expected output
    expected_output = {
        "preferences": "somepath/preferences",
        "instructions": "somepath/instructions",
        "continuation_instructions_1": "somepath/continuation_1_instructions_p2",
        "continuation_preferences_1": "somepath/continuation_1_preferences_p1",
        "continuation_preferences_2": "somepath/continuation_2_preferences_p1"
    }

    # Ensure the function returns the expected output
    output = image_processor.merge_continuation_images_into_path_selection(path_selection, continuation_sheets)
    assert output == expected_output


def test_merge_continuation_images_into_path_selection_edge_combo(image_processor):
    # Define inputs
    path_selection = {
        "preferences": "somepath/preferences",
        "instructions": "somepath/instructions"
    }
    continuation_sheets = {
        "continuation_1": {
            "p1": {
                "path": "somepath/continuation_1/preferences_p1",
                "type": "preferences"
            },
            "p2": {
                "path": "somepath/continuation_1/preferences_p2",
                "type": "preferences"
            }
        },
        "continuation_2": {
            "p1": {
                "path": "somepath/continuation_2/random_p1",
                "type": "neither"
            },
            "p2": {
                "path": "somepath/continuation_2/random_p2",
                "type": "neither"
            }
        }
    }
    # Define expected output
    expected_output = {
        "preferences": "somepath/preferences",
        "instructions": "somepath/instructions",
        "continuation_preferences_1": "somepath/continuation_1/preferences_p1",
        "continuation_preferences_2": "somepath/continuation_1/preferences_p2"
    }

    # Ensure the function returns the expected output
    output = image_processor.merge_continuation_images_into_path_selection(path_selection, continuation_sheets)
    assert output == expected_output

def test_all_mandatory_fragments_and_one_of_fragments_exist(image_processor):
    # Case for mandatory fragments exist and one of
    target_string = "This is a test string"
    mandatory_fragments = ["test", "string"]
    one_of_fragments = ["is", "a"]
    result = image_processor.string_fragments_in_string(target_string, mandatory_fragments, one_of_fragments)
    assert result == True

    # Case for not all mandatory fragments exist
    target_string = "This is a test"
    mandatory_fragments = ["test", "string"]
    one_of_fragments = ["is", "a"]
    result = image_processor.string_fragments_in_string(target_string, mandatory_fragments, one_of_fragments)
    assert result == False

    # Case none of the one of fragments exist
    target_string = "This is a test string"
    mandatory_fragments = ["test", "string"]
    one_of_fragments = ["not", "found"]
    result = image_processor.string_fragments_in_string(target_string, mandatory_fragments, one_of_fragments)
    assert result == False

    # Case empty mandatory fragments
    target_string = "This is a test string"
    mandatory_fragments = []
    one_of_fragments = ["is", "a"]
    result = image_processor.string_fragments_in_string(target_string, mandatory_fragments, one_of_fragments)
    assert result == True


    # Case empty one of fragments
    target_string = "This is a test string"
    mandatory_fragments = ["test", "string"]
    one_of_fragments = []
    result = image_processor.string_fragments_in_string(target_string, mandatory_fragments, one_of_fragments)
    assert result == False


def test_detect_marked_checkbox(image_processor):
    # Test a marked checkbox
    unmarked_checkbox_path = "/function/tests/checkbox_images/checkbox_x.jpg"
    assert image_processor.detect_marked_checkbox(unmarked_checkbox_path) == True

    # Test an unmarked checkbox
    marked_checkbox_path = "/function/tests/checkbox_images/checkbox_blank.jpg"
    assert image_processor.detect_marked_checkbox(marked_checkbox_path) == False

    # Test a marked grey checkbox
    unmarked_checkbox_path = "/function/tests/checkbox_images/checkbox_tick_grey.jpg"
    assert image_processor.detect_marked_checkbox(unmarked_checkbox_path) == True

    # Test an unmarked checkbox
    unmarked_checkbox_path = "/function/tests/checkbox_images/checkbox_tick_grey_blank.jpg"
    assert image_processor.detect_marked_checkbox(unmarked_checkbox_path) == False


@mock_secretsmanager
def test_get_secret(image_processor):
    # Create a mock Secrets Manager secret
    secret_value = "my-secret-key"
    secret_name = "testing/jwt-key"
    client = boto3.client("secretsmanager", region_name="eu-west-1")
    client.create_secret(Name=secret_name, SecretString=secret_value)
    result = image_processor.get_secret()

    # Check that the method returns the correct secret value
    assert result == secret_value

    # Test that an exception is raised when Secrets Manager cannot be accessed
    client.delete_secret(SecretId=secret_name)
    with pytest.raises(ClientError):
        image_processor.get_secret()


def test_build_sirius_headers(image_processor, monkeypatch):
    # Mock environment variable and secret manager get_secret method
    monkeypatch.setenv("SESSION_DATA", "test-session-data")
    mock_secret = "my-test-secret"

    with patch.object(image_processor, "get_secret", return_value=mock_secret):
        # Call the build_sirius_headers method
        headers = image_processor.build_sirius_headers()

        # Check that the method returns the correct headers
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"].startswith("Bearer ")

        # Decode the JWT token and check its contents
        token = headers["Authorization"][7:]
        decoded_token = jwt.decode(token, mock_secret, algorithms=["HS256"])
        assert decoded_token["session-data"] == "test-session-data"
        assert "iat" in decoded_token
        assert "exp" in decoded_token


def test_similarity_score(image_processor):
    # Test case 1: Identical strings
    str1 = "The quick brown fox jumps over the lazy dog."
    str2 = "The quick brown fox jumps over the lazy dog."
    assert image_processor.similarity_score(str1, str2) == 1.0

    # Test case 2: Completely different strings
    str1 = "Python is a programming language."
    str2 = "The quick brown fox jumps over the lazy dog."
    assert image_processor.similarity_score(str1, str2) == 0.0

    # Test case 3: Partially similar strings
    str1 = "The quick brown fox jumps over the lazy dog."
    str2 = "The quick brown fox jumps over the lazy cat."
    score = image_processor.similarity_score(str1, str2)
    assert 0.8 < score < 0.9

    # Test case 4: Case sensitivity
    str1 = "The quick brown fox jumps over the lazy dog."
    str2 = "the quick brown Fox jumps over the lazy dog."
    assert image_processor.similarity_score(str1, str2) == 1.0

    # Test case 5: Punctuation and special characters
    str1 = "The quick brown fox jumps over the lazy dog!"
    str2 = "The quick brown fox jumps over the lazy dog."
    assert image_processor.similarity_score(str1, str2) == 1.0


def test_levenstein_distance(image_processor):
    assert image_processor.levenstein_distance('kitten', 'sitting') == 3
    assert image_processor.levenstein_distance('rosettacode', 'raisethysword') == 8
    assert image_processor.levenstein_distance('', 'foo') == 3
    assert image_processor.levenstein_distance('foo', '') == 3
    assert image_processor.levenstein_distance('', '') == 0


class MockFormMeta:
    def __init__(self, form_pages):
        self.form_pages = form_pages


class MockFormPage:
    def __init__(self, barcode, page_number, page_text):
        self.additional_args = {"extra": {"barcode": barcode, "page_text": page_text}}
        self.page_number = page_number
        self.identifier = "(.*meta_page_1.*)"


@pytest.fixture
def mock_form_images_as_strings():
    return ['meta_page_1_text', 'meta_page_2_text']

@pytest.fixture
def mock_form_metastore():
    return {
        'meta_1': MockFormMeta(
            form_pages=[MockFormPage(page_number=1, barcode="", page_text="meta_page_1_text"), MockFormPage(page_number=2, barcode="", page_text="meta_page_2_text")]
        ),
        'meta_2': MockFormMeta(
            form_pages=[MockFormPage(page_number=1, barcode="", page_text="meta2_page_1_text"), MockFormPage(page_number=2, barcode="", page_text="meta2_page_2_text")]
        )
    }


def test_create_scan_to_template_distances(monkeypatch, image_processor, mock_form_images_as_strings, mock_form_metastore):
    mock_get_meta_page_text = MagicMock()
    mock_get_meta_page_text.return_value = "meta_page_1_text"
    # Call the method with a valid UID
    monkeypatch.setattr(image_processor, "get_meta_page_text", mock_get_meta_page_text)

    distances = image_processor.create_scan_to_template_distances(mock_form_images_as_strings, mock_form_metastore)

    assert len(distances) == 8  # Expect 8 distances for 2 images and 2 metas each with 2 form pages

    # Test the first distance
    assert distances[0]['meta'] == 'meta_1'
    assert distances[0]['distance'] == 0
    assert distances[0]['scan_page_no'] == 1
    assert distances[0]['template_page_no'] == 1
    assert distances[0]['form_image_as_string'] == 'meta_page_1_text'
    assert distances[0]['meta_page_text'] == 'meta_page_1_text'

    # Test the last distance
    assert distances[-1]['meta'] == 'meta_2'
    assert distances[-1]['distance'] == 1000
    assert distances[-1]['scan_page_no'] == 2
    assert distances[-1]['template_page_no'] == 2
    assert distances[-1]['form_image_as_string'] == 'meta_page_2_text'
    assert distances[-1]['meta_page_text'] == 'meta_page_1_text'
