import datetime
import json

import boto3
import jwt
import os

import requests
from app.utility.custom_logging import custom_logger
from botocore.exceptions import ClientError

logger = custom_logger("sirius_service")


class SiriusService:
    def __init__(self, environment):
        self.environment = environment
        self.target_environment = os.getenv("TARGET_ENVIRONMENT")
        self.sirius_url = os.getenv("SIRIUS_URL")
        self.sirius_url_part = os.getenv("SIRIUS_URL_PART")
        self.secret_key_prefix = os.getenv("SECRET_PREFIX")
        self.secret_manager = self.setup_secret_manager_connection()

    def build_sirius_headers(self):
        """
        Builds headers for Sirius request, including JWT auth
        Returns:
            Header dictionary with content type and auth token
        """
        content_type = "application/json"
        session_data = os.environ["SESSION_DATA"]
        secret = self.get_secret()

        encoded_jwt = jwt.encode(
            {
                "session-data": session_data,
                "iat": datetime.datetime.utcnow(),
                "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=3600),
            },
            secret,
            algorithm="HS256",
        )

        return {
            "Content-Type": content_type,
            "Authorization": "Bearer " + encoded_jwt,
        }

    def make_request_to_sirius(self, uid: str) -> dict:
        """
        Sends a GET request to the Sirius API to retrieve scans associated with a given UID.

        Args:
        - uid (str): A unique identifier for a particular record.

        Returns:
        - response_dict (dict): A dictionary containing the response from Sirius.
          If an error occurred, the dictionary will contain an "error" key with an error message as the value.
        """
        url = f"{self.sirius_url}{self.sirius_url_part}/lpas/{uid}/scans"
        headers = self.build_sirius_headers()
        logger.debug(f"Sending request to Sirius on url: {url}")

        try:
            response = requests.get(url=url, headers=headers)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error getting response from Sirius: {e}")

        try:
            response_dict = json.loads(response.text)
        except json.decoder.JSONDecodeError as e:
            raise Exception(f"Unable to decode sirius JSON: {e}")

        return response_dict

    def setup_secret_manager_connection(self) -> boto3.client:
        """
        Sets up a connection to AWS Secrets Manager based on instance variable "environment".
        If the environment is "local", the connection object will use the local endpoint URL for testing purposes.

        Returns:
        - A connection to AWS Secrets Manager (boto3.client).
        """
        if self.environment == "local":
            sm = boto3.client(
                service_name="secretsmanager",
                region_name="eu-west-1",
                endpoint_url="http://localstack-processor:4566",
                aws_access_key_id="fake",
                aws_secret_access_key="fake",  # pragma: allowlist secret
            )
        else:
            sm = boto3.client(service_name="secretsmanager", region_name="eu-west-1")
        return sm

    def get_secret(self):
        """
        Gets and decrypts the JWT secret from AWS Secrets Manager for the chosen environment
        Args:
            environment: AWS environment name
        Returns:
            JWT secret
        Raises:
            ClientError
        """
        secret_name = f"{self.secret_key_prefix}/jwt-key"

        try:
            get_secret_value_response = self.secret_manager.get_secret_value(
                SecretId=secret_name
            )
            secret = get_secret_value_response["SecretString"]
        except ClientError as e:
            raise Exception(
                f"Unable to get secret for JWT key from Secrets Manager: {e}"
            )

        return secret
