import os
import boto3
import pytest
import json
from unittest.mock import patch
from moto import mock_s3, mock_sqs
from lambdas.image_request_handler.app.handler import ImageRequestHandler
from botocore.stub import Stubber

test_uid = "700000001"
test_queue = "test-queue"
test_bucket = "test-bucket"


@pytest.fixture(autouse=True)
def setup_environment_variables():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["ENVIRONMENT"] = "testing"


@pytest.fixture
def image_request_handler():
    return ImageRequestHandler(test_uid, test_bucket, test_queue)


def test_init(image_request_handler):
    assert image_request_handler.environment == os.getenv('ENVIRONMENT')
    assert image_request_handler.uid == "700000001"
    assert image_request_handler.bucket == "test-bucket"
    assert image_request_handler.sqs_queue == "test-queue"
    assert image_request_handler.total_images == 4
    assert image_request_handler.images_to_check == [
        'iap-700000001-1',
        'iap-700000001-2',
        'iap-700000001-3',
        'iap-700000001-4',
    ]
    assert image_request_handler.url_expiration == 60


@patch('boto3.client')
def test_setup_sqs_connection(mock_boto3, image_request_handler):
    image_request_handler.setup_sqs_connection()
    if image_request_handler.environment == "local":
        mock_boto3.assert_called_with("sqs", endpoint_url="http://localstack:4566", region_name="eu-west-1")
    else:
        mock_boto3.assert_called_with("sqs", region_name="eu-west-1")


@patch('boto3.client')
def test_setup_s3_connection(mock_boto3, image_request_handler):
    image_request_handler.setup_s3_connection()
    if image_request_handler.environment == "local":
        mock_boto3.assert_called_with("s3", endpoint_url="http://localstack:4566", region_name="eu-west-1")
    else:
        mock_boto3.assert_called_with("s3", region_name="eu-west-1")


@patch.object(ImageRequestHandler, 'image_status_in_bucket')
def test_check_image_statuses(mock_image_status_in_bucket):
    images_to_check = ['image1', 'image2', 'image3', 'image4']
    mock_image_status_in_bucket.side_effect = ['NOT_FOUND', 'IN_PROGRESS', 'EXISTS', 'EXISTS']
    handler = ImageRequestHandler("700000001", "test-bucket", "test-queue")
    # Test the method with mocked return values
    image_statuses = handler.check_image_statuses(images_to_check)
    # Assert the method returns the expected statuses
    assert image_statuses == {'image1': 'NOT_FOUND', 'image2': 'IN_PROGRESS', 'image3': 'EXISTS', 'image4': 'EXISTS'}


@mock_s3
def test_image_status_in_bucket(image_request_handler):
    s3 = boto3.client('s3', region_name='us-east-1')
    bucket = 'test-bucket'
    s3.create_bucket(Bucket=bucket)
    image = 'test-image.jpg'

    # Test scenario where image exists
    s3.put_object(Bucket=bucket, Key=image, Body=b'test-content')
    result = image_request_handler.image_status_in_bucket(image)
    assert result == 'EXISTS'

    # Test scenario where image is in progress
    s3.delete_object(Bucket=bucket, Key=image)
    s3.put_object(Bucket=bucket, Key=image)
    result = image_request_handler.image_status_in_bucket(image)
    assert result == 'IN_PROGRESS'

    # Test scenario where image not found
    s3.delete_object(Bucket=bucket, Key=image)
    result = image_request_handler.image_status_in_bucket(image)
    assert result == 'NOT_FOUND'

    # Test scenario where there is an error
    error_response = {'Error': {'Code': '401', 'Message': 'Access Denied'}}
    with patch.object(image_request_handler.s3, 'head_object',
                      return_value=Exception(error_response, 'head_object')) as head_object_mock:
        response = image_request_handler.image_status_in_bucket(image)
        assert response == 'ERROR'


@mock_sqs
def test_add_to_sqs(image_request_handler):
    sqs = boto3.client('sqs', region_name='eu-west-1')
    sqs_queue = sqs.create_queue(QueueName=test_queue)['QueueUrl']
    uid = test_uid

    # Test scenario where the message is sent successfully
    image_request_handler.add_to_sqs()
    response = sqs.receive_message(QueueUrl=sqs_queue, MaxNumberOfMessages=1)
    assert response['Messages'][0]['Body'] == json.dumps({'uid': uid})

    # Test scenario where there is an error
    image_request_handler.s3 = boto3.client('sqs', region_name='eu-west-1')
    stubber = Stubber(image_request_handler.sqs)
    stubber.add_client_error('send_message')
    stubber.activate()
    with pytest.raises(Exception):
        image_request_handler.add_to_sqs()


@mock_s3
def test_add_temp_images_to_bucket():
    image_request_handler = ImageRequestHandler(test_uid, test_bucket, test_queue)
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='test-bucket')
    image_request_handler.images_to_check = ['image1.jpg', 'image2.jpg', 'image3.jpg']

    # Test scenario where the images are added to the bucket successfully
    assert image_request_handler.add_temp_images_to_bucket() is True

    image_request_handler.images_to_check = ['iap-700000001-1']

    image_request_handler.s3 = boto3.client('s3')
    stubber = Stubber(image_request_handler.s3)
    stubber.add_client_error('put_object')
    stubber.activate()
    with pytest.raises(Exception):
        image_request_handler.add_temp_images_to_bucket()


@mock_s3
def test_generate_signed_urls_returns_correct_urls():
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket=test_bucket)
    image_request_handler = ImageRequestHandler(test_uid, test_bucket, test_queue)

    image_statuses = {'image1': 'FOUND', 'image2': 'FOUND'}
    expected_urls = {
        'image1': 'https://test-bucket.s3.amazonaws.com/image1',
        'image2': 'https://test-bucket.s3.amazonaws.com/image2'
    }

    actual_urls = image_request_handler.generate_signed_urls(image_statuses)
    actual_urls['image1'] = actual_urls['image1'][0:43]
    actual_urls['image2'] = actual_urls['image2'][0:43]
    assert (actual_urls == expected_urls)


def test_formatted_message_returns_correct_message():
    signed_urls = {'image1': 'url1', 'image2': 'url2'}
    collection_status = 'SUCCESS'
    image_request_handler = ImageRequestHandler(test_uid, test_bucket, test_queue)
    actual_message = image_request_handler.formatted_message(signed_urls, collection_status)

    expected_message = {
        'uid': image_request_handler.uid,
        'status': collection_status,
        'signed_urls': signed_urls
    }

    assert actual_message == expected_message


def test_get_image_collection_status_returns_collection_in_progress(image_request_handler):
    image_statuses = {'image1': 'EXISTS', 'image2': 'IN_PROGRESS'}
    image_request_handler.total_images = len(image_statuses)

    actual_status = image_request_handler.get_image_collection_status(image_statuses)

    expected_status = 'COLLECTION_IN_PROGRESS'
    assert actual_status == expected_status


def test_get_image_collection_status_returns_collection_complete(image_request_handler):
    image_statuses = {'image1': 'EXISTS', 'image2': 'EXISTS'}
    image_request_handler.total_images = len(image_statuses)

    actual_status = image_request_handler.get_image_collection_status(image_statuses)

    expected_status = 'COLLECTION_COMPLETE'
    assert actual_status == expected_status


def test_get_image_collection_status_returns_collection_not_started(image_request_handler):
    image_statuses = {'image1': 'NOT_FOUND', 'image2': 'NOT_FOUND'}
    image_request_handler.total_images = len(image_statuses)

    actual_status = image_request_handler.get_image_collection_status(image_statuses)

    expected_status = 'COLLECTION_NOT_STARTED'
    assert actual_status == expected_status


def test_get_image_collection_status_returns_collection_error(image_request_handler):
    image_statuses = {'image1': 'EXISTS', 'image2': 'ERROR'}
    image_request_handler.total_images = len(image_statuses)

    actual_status = image_request_handler.get_image_collection_status(image_statuses)

    expected_status = 'COLLECTION_ERROR'
    assert actual_status == expected_status

@mock_s3
@mock_sqs
def test_process_request(image_request_handler):
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket=test_bucket)
    sqs = boto3.client('sqs', region_name='eu-west-1')
    sqs.create_queue(QueueName=test_queue)

    # Should not be started on first attempt
    response = image_request_handler.process_request()
    response_body = json.loads(response['body'])

    assert response['statusCode'] == 200
    assert len(response_body['signed_urls'].items()) == 4
    assert response_body['status'] == 'COLLECTION_NOT_STARTED'
    assert response_body['uid'] == test_uid

    # Check in progress on second attempt
    response = image_request_handler.process_request()
    response_body = json.loads(response['body'])

    assert response['statusCode'] == 200
    assert len(response_body['signed_urls'].items()) == 4
    assert response_body['status'] == 'COLLECTION_IN_PROGRESS'
    assert response_body['uid'] == test_uid

    stubber = Stubber(image_request_handler.s3)
    stubber.add_client_error('put_object')
    stubber.activate()
    response = image_request_handler.process_request()
    response_body = json.loads(response['body'])
    assert response['statusCode'] == 500
    assert response_body['status'] == 'COLLECTION_ERROR'
