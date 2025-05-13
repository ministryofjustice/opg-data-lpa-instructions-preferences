# Deleting the extracts from an LPA scan
Sometimes images will be distorted or unreadable, and you will need to delete the extracts from an LPA scan and initiate a new scan.

## Delete the existing extracts
This can be done by running the [\[Workflow\] Delete Instructions and Preferences of an LPA](https://github.com/ministryofjustice/opg-data-lpa-instructions-preferences/actions/workflows/delete_specific_lpa.yml) Github Actions workflow in the instructions-and-preferences repository. This workflow will delete all associated extracts from the instructions and preferences S3 bucket. It does not delete the original PDFs from the Sirius S3 bucket.

## Initiate a new scan
Once the extracts have been deleted, you can either wait for the user to initiate a new scan by accessing the Use / View service or you can initiate a new scan yourself running the following commands in a local version of the instructions-and-preferences repository:

```bash
pwd
opg-data-lpa-instructions-preferences/scripts
aws-vault exec identity -- python post-request.py -w production -u <LPA ID> | jq
```

## Viewing the images
Once the extractions have been completed, the script will return JSON with links to download the images, e.g.:

```bash
{
 "uId": <LPA-ID>
 "status": "COLLECTION_COMPLETE",
 "signedUrls": {
  "iap-<LPA-ID>-instructions": "<link>"
  "iap-<LPA-ID>-preferences": "<link>"
 }
}
```

This will return a JSON object containing links to the new extracts. Once downloaded, use the `Preview` app on Mac (it will be easier to select all related images to view at the same time) to view the images and ensure that the images are legible and undistorted.

## Dealing with errors
When an error happens, the status will be: `COLLECTION_ERROR`. Sometimes it can be preudent to rerun the extraction process once or twice if the image is wonky or has errors.

The most common errors are:
- `# extracted images were found to be too dark to be likely to be readable` - this could be an error with the scan itself, or the OCR has gotten itself in a mess. 
- `Cannot find request_id. Try extending the search period further back with the -s argument.` - if the image you're searching for dates back longer than 30 days, the script is unable to find any errorsin the logs. The `-s` or `--search-time` argument overrides this. 

## Troubleshooting
If the new extracts are still distorted or unreadable after this, you will need to contact the [code owners](https://github.com/ministryofjustice/opg-data-lpa-instructions-preferences/blob/main/CODEOWNERS) to investigate further.
