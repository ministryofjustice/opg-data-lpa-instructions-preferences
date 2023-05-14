# Tests to perform
import json
import time
import os

import config
import boto3
import requests
import pytest
from requests_aws4auth import AWS4Auth
from botocore.exceptions import ClientError

env = os.environ.get("ENVIRONMENT", "local")
workspace = os.environ.get("WORKSPACE", "local")


@pytest.fixture(autouse=True, scope="session")
def setup_rest_url_part() -> str:
    """
    Get different URL parts dependant on environment
    """
    return get_localstack_rest_api() if env == "local" else "/v1"


@pytest.fixture(autouse=True, scope="session")
def cleanup_iap_buckets() -> list:
    """
    Delete images from the IAP bucket specified in the configuration.

    Returns:
        List[str]: A list of deleted image keys.
    """
    images_to_remove = []

    # Iterate over all templates and collections in the config file
    for template, template_data in config.templates.items():
        for collection_type in [
            "expected_collection_started_response",
            "expected_collection_in_progress_response",
            "expected_collection_completed_response",
        ]:
            collection = template_data[collection_type]
            signed_urls = collection["signed_urls"]

            # Add all images to be removed to a list
            for item_to_remove, data in signed_urls.items():
                images_to_remove.append(item_to_remove)

    s3 = get_s3()
    bucket_name = f"{config.environment[env]['iap_bucket']}-{workspace}"
    images_to_remove_deduped = list(set(images_to_remove))

    deleted_images = []

    # Iterate over all images to be removed, and attempt to delete them from S3
    for image in images_to_remove_deduped:
        print(f"Trying {image}")
        try:
            s3.delete_object(Bucket=bucket_name, Key=image)
            print(f"Successfully deleted {image} from {bucket_name}")
            deleted_images.append(image)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                print(f"{image} does not exist in {bucket_name}")
            else:
                print(f"Error deleting {image} from {bucket_name}: {e}")

    return deleted_images


def get_request_auth() -> AWS4Auth:
    """
    Get the AWS4 authentication object to sign requests to API gateway.

    Returns:
        AWS4Auth: An AWS4Auth object to authenticate against API gateway requests.
    """
    if env == "local":
        access_key = "fake"
        secret_key = "fake"
        token = "fake"
    else:
        session = boto3.Session()
        credentials = session.get_credentials()
        credentials = credentials.get_frozen_credentials()
        access_key = credentials.access_key
        secret_key = credentials.secret_key
        token = credentials.token

    auth = AWS4Auth(
        access_key,
        secret_key,
        "eu-west-1",
        "execute-api",
        session_token=token,
    )
    return auth


def call_api_gateway(url: str) -> requests.Response:
    """
    Call an API Gateway endpoint and return the response.

    Args:
        url: The URL of the API Gateway endpoint to call.

    Returns:
        requests.Response: The response from the API Gateway endpoint.
    """
    auth = get_request_auth()

    response = requests.request(method="GET", url=url, auth=auth)

    return response


def get_s3() -> boto3.client:
    """
    Get an s3 client session to use for calls to s3.

    Returns:
        boto3.client: An s3 client session.
    """
    # If running locally, use a custom endpoint and fake credentials
    if env == "local":
        session = boto3.Session(
            region_name="eu-west-1",
            aws_access_key_id="fake",
            aws_secret_access_key="fake",
        )
        s3_client = session.client(
            "s3", endpoint_url="http://localhost:4566", region_name="eu-west-1"
        )
    # Otherwise, use default credentials
    else:
        s3_client = boto3.client("s3")
    return s3_client


def get_localstack_rest_api() -> str:
    """
    Get the base path of the first REST API in the LocalStack API Gateway.

    Returns:
        str: The base path of the first REST API in the LocalStack API Gateway.
    """
    session = boto3.Session(
        region_name="eu-west-1", aws_access_key_id="fake", aws_secret_access_key="fake"
    )
    apigateway = session.client(
        "apigateway", endpoint_url="http://localhost:4566", region_name="eu-west-1"
    )
    response = apigateway.get_rest_apis()

    return f"/restapis/{response['items'][0]['id']}/v1/_user_request_"


def make_calls_and_assertions(response_type, setup_rest_url_part) -> None:
    """
    Make API calls and assert the response matches the expected response
    """
    for template, template_data in config.templates.items():
        print(
            f"Asserting responses for template: {template} with response type: {response_type}"
        )

        if env == "local":
            url = f'http://localhost:4566{setup_rest_url_part}/image-request/{template_data["lpa_uid"]}'
        else:
            workspace_url_part = (
                "dev" if workspace == "development" else f"{workspace}.dev"
            )
            url = (
                f"https://{workspace_url_part}.lpa-iap.api.opg.service.justice.gov.uk{setup_rest_url_part}"
                f'/image-request/{template_data["lpa_uid"]}'
            )

        print(f"url for api gateway: {url}")
        response = call_api_gateway(url)
        response_object = json.loads(response.text)

        assert response.status_code == 200
        assert response_object["status"] == template_data[response_type]["status"]
        assert len(response_object["signed_urls"]) == len(
            template_data[response_type]["signed_urls"]
        )


@pytest.mark.order(1)
def test_collection_started(setup_rest_url_part):
    make_calls_and_assertions(
        "expected_collection_started_response", setup_rest_url_part
    )


@pytest.mark.order(2)
def test_collection_in_progress(setup_rest_url_part):
    make_calls_and_assertions(
        "expected_collection_in_progress_response", setup_rest_url_part
    )


@pytest.mark.order(3)
def test_collection_completed(setup_rest_url_part):
    total_sleep_time = 5 * 60  # sleep for 5 minutes
    time_remaining = total_sleep_time

    while time_remaining > 0:
        print(f"Time remaining: {time_remaining} seconds")
        time.sleep(30)  # sleep for 30 seconds
        time_remaining -= 30
    make_calls_and_assertions(
        "expected_collection_completed_response", setup_rest_url_part
    )
