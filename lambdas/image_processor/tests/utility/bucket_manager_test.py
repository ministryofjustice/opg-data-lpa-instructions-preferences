import os
import boto3
from unittest.mock import patch, MagicMock
from moto import mock_s3
import pytest
from app.utility.bucket_manager import BucketManager


@pytest.fixture(autouse=True)
def setup_environment_variables():
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["TARGET_ENVIRONMENT"] = "target-testing"


@pytest.fixture
def bucket_manager():
    return BucketManager()


def test_extract_s3_file_path(bucket_manager):
    s3_path = "s3://my_bucket/my_scan.pdf"
    expected_result = {"bucket": "my_bucket", "file_path": "my_scan.pdf"}
    assert bucket_manager.extract_s3_file_path(s3_path) == expected_result

    s3_path = "s3://my_bucket/folder1/folder2/my_scan.pdf"
    expected_result = {
        "bucket": "my_bucket",
        "file_path": "folder1/folder2/my_scan.pdf",
    }
    assert bucket_manager.extract_s3_file_path(s3_path) == expected_result

    s3_path = "s3://my_bucket/"
    expected_result = {"bucket": "my_bucket", "file_path": ""}
    assert bucket_manager.extract_s3_file_path(s3_path) == expected_result


@patch("boto3.client")
def test_setup_s3_connection(mock_boto3, bucket_manager):
    bucket_manager.setup_s3_connection()
    if bucket_manager.environment == "local":
        mock_boto3.assert_called_with(
            "s3", endpoint_url="http://localstack:4566", region_name="eu-west-1"
        )
    else:
        mock_boto3.assert_called_with("s3", region_name="eu-west-1")


def test_download_scanned_images(bucket_manager, monkeypatch):
    # Define test data
    s3_urls_dict = {
        "lpaScans": [{"location": "s3://my_bucket/my_scan.pdf", "template": "TEST"}],
        "continuationSheets": [
            {
                "location": "s3://my_bucket/my_continuation_sheet1.pdf",
                "template": "TEST",
            },
            {
                "location": "s3://my_bucket/my_continuation_sheet2.pdf",
                "template": "TEST",
            },
        ],
    }
    output_folder_path = "/tmp/output"
    # Define mock objects
    mock_s3 = MagicMock()
    mock_download_file = MagicMock()
    mock_s3.download_file = mock_download_file
    monkeypatch.setattr(bucket_manager, "s3", mock_s3)

    # Run the function to test
    result = bucket_manager.download_scanned_images(s3_urls_dict, output_folder_path)

    # Check that the expected S3 files were downloaded
    assert len(mock_download_file.mock_calls) == 3
    mock_download_file.assert_any_call(
        "my_bucket", "my_scan.pdf", "/tmp/output/my_scan.pdf"
    )
    mock_download_file.assert_any_call(
        "my_bucket",
        "my_continuation_sheet1.pdf",
        "/tmp/output/my_continuation_sheet1.pdf",
    )
    mock_download_file.assert_any_call(
        "my_bucket",
        "my_continuation_sheet2.pdf",
        "/tmp/output/my_continuation_sheet2.pdf",
    )

    # Check that the function returned the expected file paths
    expected_result = {
        "scans": ["/tmp/output/my_scan.pdf"],
        "continuations": {
            "continuation_1": "/tmp/output/my_continuation_sheet1.pdf",
            "continuation_2": "/tmp/output/my_continuation_sheet2.pdf",
        },
    }

    assert result == expected_result


@mock_s3
def test_put_images_to_bucket(bucket_manager):
    s3 = boto3.client("s3", region_name="us-east-1")
    iap_bucket = "my-test-bucket"
    uid = "700000000001"
    bucket_manager.s3 = s3
    bucket_manager.iap_bucket = iap_bucket
    s3.create_bucket(Bucket=iap_bucket)

    # Create a test file
    test_file_content = b"Test file content"
    test_file_key = "testfile"
    test_file_path = f"/tmp/{test_file_key}.jpg"
    with open(test_file_path, "wb") as f:
        f.write(test_file_content)

    # Call the method being tested
    path_selection = {test_file_key: test_file_path}
    bucket_manager.put_images_to_bucket(
        path_selection=path_selection,
        uid=uid,
        continuation_instruction_count=0,
        continuation_preference_count=0,
        continuation_unknown_count=0,
    )

    # Check that the file was uploaded to S3
    response = s3.get_object(Bucket=iap_bucket, Key=f"iap-{uid}-{test_file_key}")
    assert response["Body"].read() == test_file_content
    head = s3.head_object(Bucket=iap_bucket, Key=f"iap-{uid}-{test_file_key}")
    assert head["Metadata"] == {
        "continuationsheetsinstructions": "0",
        "continuationsheetspreferences": "0",
        "continuationsheetsunknown": "0",
        "processerror": "0",
    }


@mock_s3
def test_put_error_image_to_bucket(bucket_manager):
    s3 = boto3.client("s3", region_name="us-east-1")
    iap_bucket = "my-test-bucket"
    uid = "700000000001"
    bucket_manager.s3 = s3
    bucket_manager.iap_bucket = iap_bucket
    s3.create_bucket(Bucket=iap_bucket)

    bucket_manager.put_error_image_to_bucket(uid=uid)

    # Check that the file was uploaded to S3
    head = s3.head_object(Bucket=iap_bucket, Key=f"iap-{uid}-instructions")
    assert head["Metadata"] == {
        "continuationsheetsinstructions": "0",
        "continuationsheetspreferences": "0",
        "continuationsheetsunknown": "0",
        "processerror": "1",
    }