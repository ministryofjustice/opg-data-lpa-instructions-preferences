module "ual_iap_s3" {
  source = "./modules/s3_bucket"

  account_name                = local.account.name
  bucket_name                 = "lpa-iap-${local.environment}"
  force_destroy               = local.account.force_destroy_bucket
  kms_key_id                  = data.aws_kms_key.ual_iap_s3.id
  enable_lifecycle            = true
  expiration_days             = local.expiration_days
  non_current_expiration_days = local.noncurrent_expiration_days
  providers = {
    aws = aws
  }
}

locals {
  use_url = local.environment == "production" ? "https://use-lasting-power-of-attorney.service.gov.uk" : "https://${local.environment}.use-lasting-power-of-attorney.service.gov.uk"
}

resource "aws_s3_bucket_cors_configuration" "ual_iap_s3" {
  bucket = module.ual_iap_s3.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET"]
    allowed_origins = [local.use_url]
    max_age_seconds = 3000
  }
}
