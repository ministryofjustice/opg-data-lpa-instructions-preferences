module "ual_iap_s3" {
  source = "./s3_bucket"

  account_name                         = local.account.name
  bucket_name                          = "ual-iap-${local.environment}"
  force_destroy                        = local.account.force_destroy_bucket
  kms_key_id                           = data.aws_kms_key.ual_iap_s3.id
  environment_name                     = local.environment
  enable_lifecycle                     = true
  allowed_roles                        = [aws_iam_role.ual_iap_lambda_execution_role.arn]
  expiration_days                      = local.expiration_days
  non_current_expiration_days          = local.noncurrent_expiration_days
  providers = {
    aws = aws
  }
}

data "aws_kms_key" "ual_iap_s3" {
  key_id = "alias/s3-ual-iap-${local.account.name}"
}
