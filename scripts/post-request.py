#!/usr/bin/env python3

import boto3
import requests
from requests_aws4auth import AWS4Auth
import argparse


def get_role_session(environment, role):
    account = {"sirius-dev": "288342028542", "sirius-prod": "649098267436"}
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
    response = requests.request(method=method, url=url, auth=auth)
    print(response.text)
    print(response.status_code)


def main():
    arg_parser = argparse.ArgumentParser(
        description="Check specified LPA ID(s) against the Instructions and Preferences Gateway"
    )

    arg_parser.add_argument(
        "-u", "--uid", help="UID of LPA to be checked", required=True, type=int
    )

    arg_parser.add_argument(
        "-a",
        "--api",
        help="Version of the API to run against",
        default="v1",
    )

    arg_parser.add_argument(
        "-w",
        "--workspace",
        help="Environment to run against",
        choices=["development", "preproduction", "production"],
        default="development",
    )

    args = arg_parser.parse_args()

    uid = args.uid
    ver = args.api
    workspace = args.workspace

    workspace_mapping = {
        "development": "dev.",
        "preproduction": "pre.",
        "production": "",
    }
    role_session = {
        "development": "sirius-dev",
        "preproduction": "sirius-pre",
        "production": "sirius-prod",
    }
    try:
        branch_prefix = workspace_mapping[workspace]
    except KeyError:
        branch_prefix = f"{workspace}.dev."

    session = get_role_session(role_session[workspace], "operator")
    credentials = session.get_credentials()
    auth = get_request_auth(credentials)

    iap_request_url = f"https://{branch_prefix}lpa-iap.api.opg.service.justice.gov.uk/{ver}/image-request/{uid}"
    handle_request("GET", iap_request_url, auth)


if __name__ == "__main__":
    main()
