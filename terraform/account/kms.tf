resource "aws_kms_key" "s3" {
  description             = "UAL Instructions and Preferences S3 bucket encryption key"
  deletion_window_in_days = 10
  enable_key_rotation     = true
}

resource "aws_kms_alias" "s3" {
  name          = "alias/s3-ual-iap-${terraform.workspace}"
  target_key_id = aws_kms_key.s3.key_id
}
