data "aws_kms_key" "ual_iap_s3" {
  key_id = "alias/lpa-iap-s3-${local.account.name}"
}

data "aws_kms_key" "lpa_iap_logs" {
  key_id = "alias/lpa-iap-logs-${local.account.name}"
}

data "aws_kms_key" "lpa_iap_sns" {
  key_id = "alias/lpa-iap-sns-${local.account.name}"
}
