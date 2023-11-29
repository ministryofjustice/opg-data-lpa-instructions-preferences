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

This will return a JSON object containing links to the new extracts. You can then use these links to check the new extracts are readable and undistorted.

## Troubleshooting
If the new extracts are still distorted or unreadable after this, you will need to contact the [code owners](https://github.com/ministryofjustice/opg-data-lpa-instructions-preferences/blob/main/CODEOWNERS) to investigate further.
