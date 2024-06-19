# Post Request

Extracts the Instructions and Preferences for an existing LPA. If the LPA does not exist, running the script will begin a new image extraction. 

## Prerequisites 

This script will use your AWS credentials to assume the operator role in the sirius-dev or sirius-prod environment. 

Install pip modules

```bash
pip install -r requirements.txt
```

## Running the script

The script will:

	1.	Query the LPA Instructions and Preferences API for the specified LPA ID.
	2.	If a collection error is found, search CloudWatch logs for related error messages.
	3.	Print the combined API response and error messages.

To execute the script, use the following command. Replace `<ENVIRONMENT>` with `development`, `preproduction` or `production`. Replace `<LPA_ID>` with the ID of the LPA you're extracting the images for.

```bash
aws-vault exec identity -- python3 post-request.py -w <ENVIRONMENT> -u <LPA_ID> | jq
```

## Usage

```bash
options:
  -h, --help            show this help message and exit
  -u UID, --uid UID     UID of LPA to be checked
  -a API, --api API     Version of the API to run against
  -s SEARCH_TIME, --search-time SEARCH_TIME
                        How far back to search the logs in days
  -w {development,preproduction,production}, --workspace {development,preproduction,production}
                        Environment to run against
```

If the LPA has been recently deleted, you will get a `COLLECTION_STARTED` message. Wait a few minutes for this to process then rerun the script.


## Example Output

The script outputs a JSON object combining the API response and any extracted error messages. Here is an example of successful output:
```bash
{
  "uId": 123456789,
  "status": "COLLECTION_COMPLETE",
  "signedUrls": {
    "iap-123456789-instructions": "<instruction_url>",
    "iap-123456789-preferences": "<preference_url>"
  }
}
```

Upon failed extraction it will provide an error message to explain why the collection failed. If there's no error message, try extending the search period with the `-s` flag:
 ```bash
 {
  "uId": 123456789,
  "status": "COLLECTION_ERROR",
  "signedUrls": {},
  "error_messages": "Cannot find request_id. Try extending the search period further back with the -s argument."
}
```