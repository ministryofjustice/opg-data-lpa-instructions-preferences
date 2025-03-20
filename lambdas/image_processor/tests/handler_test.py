import datetime
import os
import pytest
from unittest.mock import patch
from app.handler import ImageProcessor

test_uid = "700000005"
test_queue = "test-queue"
test_bucket = "test-bucket"
event = {"Records": [{"body": '{"uid": "700000000005"}'}]}


class FakeContext:
    def __init__(self, aws_request_id: str = "999999999999"):
        self.aws_request_id = aws_request_id


@pytest.fixture(autouse=True)
def setup_environment_variables():
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["SESSION_DATA"] = "ops@email.com"


@pytest.fixture
def image_processor():
    context = FakeContext()
    return ImageProcessor(event, context)


def test_init_function(image_processor, monkeypatch):
    assert image_processor.environment == os.getenv("ENVIRONMENT")
    assert image_processor.event == event
    assert image_processor.extraction_folder_path == "extraction"
    assert image_processor.output_folder_path == "/tmp/output"
    assert int(image_processor.folder_name) > 1600000000
    assert image_processor.continuation_instruction_count == 0
    assert image_processor.continuation_preference_count == 0
    assert image_processor.uid == ""


@patch("os.walk")
def test_list_files(mock_walk, image_processor):
    # Create a mock file system to test the function
    mock_walk.return_value = [
        ("/test", ["dir1", "dir2"], ["file1.txt", "file2.png"]),
        ("/test/dir1", [], ["file3.txt", "file4.pdf"]),
        ("/test/dir2", [], ["file5.txt", "file6.jpg"]),
    ]

    # Test the function with a specified filepath and filetype
    file_paths = image_processor.list_files("/test", ".txt")

    # Verify that the correct file paths are returned
    assert file_paths == [
        "/test/file1.txt",
        "/test/dir1/file3.txt",
        "/test/dir2/file5.txt",
    ]


def test_get_timestamp_as_str(image_processor):
    # Get the current timestamp as a string
    timestamp_str = image_processor.get_timestamp_as_str()

    # Verify that the timestamp string is correct
    expected_str = str(int(datetime.datetime.now(datetime.UTC).timestamp()))
    assert timestamp_str == expected_str


def test_create_output_dir(tmpdir, image_processor):
    # Create a temporary directory to use as the output folder
    # output_dir = str(tmpdir.join('output'))
    image_processor.output_folder_path = str(tmpdir.join("output"))
    # Call the method
    image_processor.create_output_dir()
    # Check that the output directory and subdirectories were created
    assert os.path.exists(image_processor.output_folder_path)
    assert os.path.exists(os.path.join(image_processor.output_folder_path, "pass"))
    assert os.path.exists(os.path.join(image_processor.output_folder_path, "fail"))


def test_get_uid_from_event(image_processor):
    assert image_processor.get_uid_from_event() == "700000000005"


def test_update_continuation_sheet_counts(image_processor):
    paths_to_extracted_images = {
        "continuation_instructions_1": "/path/to/image1",
        "continuation_instructions_2": "/path/to/image2",
        "continuation_preferences_1": "/path/to/image3",
    }

    image_processor.update_continuation_sheet_counts(paths_to_extracted_images)

    assert image_processor.continuation_instruction_count == 2
    assert image_processor.continuation_preference_count == 1


def test_update_continuation_sheet_counts_with_no_continuation_sheets(image_processor):
    paths_to_extracted_images = {
        "some_other_sheet_1": "/path/to/image1",
        "some_other_sheet_2": "/path/to/image2",
    }

    image_processor.update_continuation_sheet_counts(paths_to_extracted_images)

    assert image_processor.continuation_instruction_count == 0
    assert image_processor.continuation_preference_count == 0


# def test_cleanup(image_processor, tmpdir):
#     # Create a temporary directory to use as the output folder path
#     output_folder_path = str(tmpdir.join("output"))
#
#     # Create a test PDF file that is more than 1 hour old
#     old_pdf_file_path = os.path.join(output_folder_path, "old.pdf")
#     with open(old_pdf_file_path, "w") as f:
#         f.write("This is an old PDF file.")
#     os.utime(old_pdf_file_path, (time.time() - 7200, time.time() - 7200))
#
#     # Create a test pass folder that is more than 1 hour old
#     old_pass_folder_path = os.path.join(output_folder_path, "pass", "1234567890")
#     os.makedirs(old_pass_folder_path)
#     os.utime(old_pass_folder_path, (time.time() - 7200, time.time() - 7200))
#
#     # Create a test fail folder that is less than 1 hour old
#     new_fail_folder_path = os.path.join(output_folder_path, "fail", "1234567890")
#     os.makedirs(new_fail_folder_path)
#
#     # Create an instance of MyClass with the temporary directory as the output folder path
#     image_processor.output_folder_path = output_folder_path
#
#     # Define the input dictionary for the cleanup method
#     downloaded_document_locations = {
#         "scans": [old_pdf_file_path],
#         "continuations": {"test": new_fail_folder_path},
#     }
#
#     # Call the cleanup method
#     output_folder_path.cleanup(downloaded_document_locations)
#     # Check that the old PDF file was deleted
#     assert not os.path.exists(old_pdf_file_path)
#     # Check that the old pass folder was deleted
#     assert not os.path.exists(old_pass_folder_path)
#     # Check that the new fail folder was not deleted
#     assert os.path.exists(new_fail_folder_path)
#     # Check that the temporary output folder was not deleted
#     assert os.path.exists(output_folder_path)
