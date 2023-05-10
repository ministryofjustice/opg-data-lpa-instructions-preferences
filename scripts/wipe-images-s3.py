import boto3


def create_s3_resource():
    """
    Assume the specified role and return the temporary credentials
    """
    # Role to assume and session name
    role_arn = "arn:aws:iam::288342028542:role/operator"
    session_name = "wipe-iap-images"

    sts_client = boto3.client("sts")
    response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName=session_name)
    credentials = response["Credentials"]

    # Create a session with the temporary credentials
    session = boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )

    # Create a client for the S3 service using the temporary credentials
    return session.resource("s3")


environment = "development"  # Add your workspace here
substrings_to_delete = ["700000158894", "700000158985", "700000159041"]
bucket_name = f"lpa-iap-{environment}"

s3 = create_s3_resource()

bucket = s3.Bucket(bucket_name)

# Iterate over all objects in the bucket
for obj in bucket.objects.all():
    # Check if the object's key contains the substring to delete
    for substring_to_delete in substrings_to_delete:
        if substring_to_delete in obj.key:
            # Delete the object
            obj.delete()
            print(f"Deleted object: {obj.key}")
