import boto3
from botocore.client import Config

# Very basic script used to get the format of the signed URLs


def assume_role(role_arn, session_name):
    """
    Assume the specified role and return the temporary credentials
    """
    sts_client = boto3.client("sts")
    response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName=session_name)
    return response["Credentials"]


# Role to assume and session name
role_arn = "arn:aws:iam::248804316466:role/breakglass"
session_name = "session-name"

# Assume the role
credentials = assume_role(role_arn, session_name)

# Create a session with the temporary credentials
session = boto3.Session(
    aws_access_key_id=credentials["AccessKeyId"],
    aws_secret_access_key=credentials["SecretAccessKey"],
    aws_session_token=credentials["SessionToken"],
)

# Create a client for the S3 service using the temporary credentials
s3_client = session.client("s3", config=Config(signature_version="s3v4"))

# Bucket name and object key
bucket_name = "my-bucket"
object_key = "my-file"

# Expiration time for the URL (10 minutes from now)
expiration = 600

# Get a signed URL for the object
url = s3_client.generate_presigned_url(
    "get_object",
    Params={"Bucket": bucket_name, "Key": object_key},
    ExpiresIn=expiration,
)

print(url)
