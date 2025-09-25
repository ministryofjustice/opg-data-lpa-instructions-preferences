resource "aws_api_gateway_rest_api" "lpa_iap" {
  name        = "lpa-instructions-preferences-${local.environment}"
  description = "API Gateway for LPA instructions and preferences - ${local.environment}"
  body        = templatefile("../../docs/openapi/${local.api_name}.yml", local.api_template_vars)
  policy      = sensitive(data.aws_iam_policy_document.lpa_iap_policy.json)

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

data "aws_iam_policy_document" "lpa_iap_policy" {
  override_policy_documents = local.ip_restrictions_enabled ? [data.aws_iam_policy_document.lpa_iap_ip_restriction_policy[0].json] : []
  statement {
    sid    = "AllowExecuteByAllowedRoles"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = local.allowed_roles
    }
    actions   = ["execute-api:Invoke"]
    resources = ["arn:aws:execute-api:eu-west-?:${local.account.account_id}:*/*/*/*"]
  }
}

data "aws_iam_policy_document" "lpa_iap_ip_restriction_policy" {
  count = local.ip_restrictions_enabled ? 1 : 0
  statement {
    sid    = "DenyExecuteByNoneAllowedIPRanges"
    effect = "Deny"
    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
    actions       = ["execute-api:Invoke"]
    not_resources = ["arn:aws:execute-api:eu-west-?:${local.account.account_id}:*/*/*/healthcheck"]
    condition {
      test     = "NotIpAddress"
      variable = "aws:SourceIp"
      values   = sensitive(local.allow_list_mapping[local.account.name])
    }
  }
}

module "allow_list" {
  source = "git@github.com:ministryofjustice/opg-terraform-aws-moj-ip-allow-list.git?ref=v3.4.5"
}

locals {
  allow_list_mapping = {
    development = concat(
      module.allow_list.use_an_lpa_development,
      module.allow_list.use_an_lpa_preproduction,
      module.allow_list.sirius_dev_allow_list,
    )
    preproduction = concat(
      module.allow_list.use_an_lpa_preproduction,
      module.allow_list.sirius_pre_allow_list,
    )
    production = concat(
      module.allow_list.use_an_lpa_production,
      module.allow_list.sirius_prod_allow_list,
    )
  }
  ip_restrictions_enabled = contains(["preproduction"], local.account.name)
}
