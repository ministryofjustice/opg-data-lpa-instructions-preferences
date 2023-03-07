import boto3
import requests
from requests_aws4auth import AWS4Auth


def get_role_session(environment, role):
    account = {"sirius-dev": "288342028542"}
    client = boto3.client("sts")

    role_to_assume = f"arn:aws:iam::{account[environment]}:role/{role}"
    response = client.assume_role(
        RoleArn=role_to_assume, RoleSessionName="IapConnectionScript"
    )

    session = boto3.Session(
        aws_access_key_id=response["Credentials"]["AccessKeyId"],
        aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
        aws_session_token=response["Credentials"]["SessionToken"],
    )

    return session


def get_request_auth(credentials):
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


def handle_request(method, url, auth):
    response = requests.request(
        method=method, url=url, auth=auth
    )
    print(response.text)
    print(response.status_code)


def main():
    branch_prefix = "uml2769"
    uid = "700000000047"
    ver = "v1"

    session = get_role_session("sirius-dev", "operator")
    credentials = session.get_credentials()
    auth = get_request_auth(credentials)

    iap_request_url = f"https://{branch_prefix}.dev.lpa-iap.api.opg.service.justice.gov.uk/{ver}/image-request/{uid}"
    handle_request("GET", iap_request_url, auth)


if __name__ == "__main__":
    main()
