import jwt
import os
import boto3
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_aws

import requests
from app.utility.sirius_service import SiriusService

test_uid = "700000000005"


@pytest.fixture(autouse=True)
def setup_environment_variables():
    os.environ["TARGET_ENVIRONMENT"] = "target-testing"
    os.environ["SIRIUS_URL"] = "http://sirius-test"
    os.environ["SIRIUS_URL_PART"] = ""
    os.environ["SECRET_PREFIX"] = "testing"


@pytest.fixture
def sirius_service():
    return SiriusService("testing")


def test_build_sirius_headers(sirius_service, monkeypatch):
    # Mock environment variable and secret manager get_secret method
    monkeypatch.setenv("SESSION_DATA", "test-session-data")
    mock_secret = "my-test-secret"

    with patch.object(sirius_service, "get_secret", return_value=mock_secret):
        # Call the build_sirius_headers method
        headers = sirius_service.build_sirius_headers()

        # Check that the method returns the correct headers
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"].startswith("Bearer ")

        # Decode the JWT token and check its contents
        token = headers["Authorization"][7:]
        decoded_token = jwt.decode(token, mock_secret, algorithms=["HS256"])
        assert decoded_token["session-data"] == "test-session-data"
        assert "iat" in decoded_token
        assert "exp" in decoded_token


@pytest.fixture
def mock_get():
    with patch("app.utility.sirius_service.requests.get") as mock_get:
        yield mock_get


def test_make_request_to_sirius_successful(mock_get, monkeypatch, sirius_service):
    # Setup the mock response
    mock_response = MagicMock()
    mock_response.text = '{"key": "value"}'
    mock_get.return_value = mock_response

    mock_sirius_headers = MagicMock()
    mock_sirius_headers.return_value = {
        "Content-Type": "application/json",
        "Authorization": "Bearer 1234",
    }
    # Call the method with a valid UID
    monkeypatch.setattr(sirius_service, "build_sirius_headers", mock_sirius_headers)
    response_dict = sirius_service.make_request_to_sirius(test_uid)

    # Verify the response
    assert response_dict == {"key": "value"}


def test_make_request_to_sirius_exception(mock_get, monkeypatch, sirius_service):
    # Setup the mock request exception
    mock_get.side_effect = requests.exceptions.RequestException("Test Exception")

    mock_sirius_headers = MagicMock()
    mock_sirius_headers.return_value = {
        "Content-Type": "application/json",
        "Authorization": "Bearer 1234",
    }
    monkeypatch.setattr(sirius_service, "build_sirius_headers", mock_sirius_headers)
    # Call the method with a valid UID
    with pytest.raises(Exception) as e:
        _ = sirius_service.make_request_to_sirius(test_uid)

    assert str(e.value) == "Error getting response from Sirius: Test Exception"


def test_make_request_to_sirius_decode_exception(mock_get, monkeypatch, sirius_service):
    # Setup the mock response
    mock_response = MagicMock()
    mock_response.text = "Invalid JSON"
    mock_get.return_value = mock_response

    mock_sirius_headers = MagicMock()
    mock_sirius_headers.return_value = {
        "Content-Type": "application/json",
        "Authorization": "Bearer 1234",
    }
    monkeypatch.setattr(sirius_service, "build_sirius_headers", mock_sirius_headers)

    with pytest.raises(Exception) as e:
        _ = sirius_service.make_request_to_sirius(test_uid)

    assert (
        str(e.value)
        == "Unable to decode sirius JSON: Expecting value: line 1 column 1 (char 0)"
    )


@mock_aws
def test_setup_secret_manager_connection(sirius_service):
    sm = sirius_service.setup_secret_manager_connection()

    # check that we can create a secret
    secret_name = "test-secret"
    secret_value = "my-secret-value"
    sm.create_secret(Name=secret_name, SecretString=secret_value)

    # check that we can retrieve the secret
    retrieved_secret = sm.get_secret_value(SecretId=secret_name)
    assert retrieved_secret["SecretString"] == secret_value


@mock_aws
def test_get_secret(sirius_service):
    # Create a mock Secrets Manager secret
    secret_value = "my-secret-key"
    secret_name = "testing/jwt-key"
    client = boto3.client("secretsmanager", region_name="eu-west-1")
    client.create_secret(Name=secret_name, SecretString=secret_value)
    result = sirius_service.get_secret()

    # Check that the method returns the correct secret value
    assert result == secret_value

    # Test that an exception is raised when Secrets Manager cannot be accessed
    client.delete_secret(SecretId=secret_name)
    with pytest.raises(Exception) as e:
        sirius_service.get_secret()
    assert "Unable to get secret for JWT key from Secrets Manager" in str(e)
