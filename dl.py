import boto3

s3 = boto3.client("s3", region_name="eu-west-1")

s3.download_file(
    "opg-backoffice-datastore-integration",
    "700000000229_201910100953160.88281500_LP1F.pdf",
    "/tmp/output/700000000229_201910100953160.88281500_LP1F.pdf"
)
