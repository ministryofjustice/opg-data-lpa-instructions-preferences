#!/usr/bin/env python3

import boto3
import requests
from requests_aws4auth import AWS4Auth
import argparse
from datetime import datetime, timedelta
import time
import json
import sys


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
    while True:
        response = requests.request(method=method, url=url, auth=auth)
        if response.status_code == 200:
            response_json = response.json()
            status = response_json.get("status")
            if status in ["COLLECTION_ERROR", "COLLECTION_COMPLETE"]:
                return response
            else:
                print(f"{status}. Retrying in 10 seconds...", file=sys.stderr)
                time.sleep(10)


def start_query(client, log_group, query, search_time):
    start_query_response = client.start_query(
        logGroupName=log_group,
        startTime=int((datetime.today() - timedelta(days=search_time)).timestamp()),
        endTime=int(datetime.now().timestamp()),
        queryString=query,
    )

    query_id = start_query_response['queryId']
    response = None

    # Keep retrying until we get a response. This could be a while due to configurable
    # search duration, so we'll let the user cancel if necessary 
    while response is None or response['status'] == 'Running':
        time.sleep(1)
        response = client.get_query_results(queryId=query_id)

    return response


def query_cloudwatch(session, log_group, query, search_time):
    client = session.client('logs')
    response = start_query(client, log_group, query, search_time)

    if response and response['status'] == 'Complete':
        return response['results']
    
    return []


def extract_request_id_and_message(log_results):
    """Extract the request_id to further search the logs"""
    for result in log_results:
        for field in result:
            if field['field'] == '@message':
                message = field['value']
                try:
                    message_json = json.loads(message.split(' - ERROR - ')[-1].strip())
                    request_id = message_json.get('request_id')
                    if request_id:
                        return request_id, message_json
                except json.JSONDecodeError:
                    print("Failed to parse message as JSON", file=sys.stderr)
                    print(json.JSONDecodeError)
    return None, None


def filter_error_messages(log_results):
    """Extract the error message to display to the user"""
    error_messages = []
    
    for result in log_results:
        for field in result:
            if field['field'] == '@message' and 'ERROR' in field['value']:
                message = field['value']
                try:
                    # Find the start and end for the part we want to keep
                    start = message.index('ERROR - ') + len('ERROR - ')
                    end = message.index(' ---', start)
                    
                    # Extract the part between 'ERROR - ' and ' ---'
                    error_message = message[start:end].strip()
                    
                    # Further remove the request_id (first part before the first space)
                    error_message = ' '.join(error_message.split(' ')[1:]).strip()
                    
                    error_messages.append(error_message)
                except ValueError:
                    # If expected parts are not found, ignore this message
                    continue
    
    return error_messages


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
        "-s",
        "--search-time",
        help="How far back to search the logs in days",
        required=False,
        type=int,
        default=1,
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
    search_time = args.search_time
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

    session = get_role_session(role_session[workspace], "breakglass")
    credentials = session.get_credentials()
    auth = get_request_auth(credentials)

    iap_request_url = f"https://{branch_prefix}lpa-iap.api.opg.service.justice.gov.uk/{ver}/image-request/{uid}"


    response = handle_request("GET", iap_request_url, auth)


    if response.status_code == 200:
        combined_output = response.json()
        print("Fetching results...", file=sys.stderr)

        if combined_output.get("status") == "COLLECTION_ERROR":
            log_group = f'/aws/lambda/lpa-iap-processor-{workspace}'

            log_results = query_cloudwatch(
                session, log_group,
                f'fields @ingestionTime, @log, @logStream, @message, @requestId, @timestamp | filter @message like /{uid}/',
                search_time=search_time
            )

            request_id, log_message = extract_request_id_and_message(log_results)

            if request_id and log_message:
                error_log_results = query_cloudwatch(
                    session, log_group,
                    f'fields @message, requestId | filter @requestId like /{request_id}/',
                    search_time=search_time
                )
                combined_output["error_messages"] = filter_error_messages(error_log_results)
            elif request_id is None:
                # If there's no error message alongside COLLECTION_ERROR, this could be due to the search period being too short
                combined_output["error_messages"] = "Cannot find request_id. Try extending the search period further back with the -s argument."
        if combined_output.get("status") != "COLLECTION_IN_PROGRESS":
            print(json.dumps(combined_output, indent=4))
    else:
        print(f"Failed to fetch data from API. Status code: {response.status_code}")



if __name__ == "__main__":
    main()