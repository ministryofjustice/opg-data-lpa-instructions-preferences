locals {
  environment        = terraform.workspace
  account            = contains(keys(var.accounts), local.environment) ? var.accounts[local.environment] : var.accounts.development
  branch_build_flag  = contains(keys(var.accounts), local.environment) ? false : true
  a_record           = local.branch_build_flag ? "${local.environment}.${data.aws_route53_zone.environment_cert.name}" : data.aws_route53_zone.environment_cert.name
  api_name           = "image-request-handler"
  target_environment = contains(keys(var.environment_mapping), local.environment) ? var.environment_mapping[local.environment] : var.environment_mapping.default

  expiration_days            = 365
  noncurrent_expiration_days = 30

  ual_api_task_env = local.account.name == "development" ? "demo" : local.account.name

  allowed_roles = tolist(concat(["arn:aws:iam::${local.account.ual_account_id}:role/${local.ual_api_task_env}-api-task-role"], local.account.extra_allowed_roles))

  api_template_vars = {
    region        = "eu-west-1"
    environment   = local.environment
    account_id    = local.account.account_id
  }

  session_data = local.account.name == "development" ? "publicapi@opgtest.com" : "opg+publicapi@digital.justice.gov.uk"
}

variable "default_role" {
  default     = "integrations-ci"
  type        = string
  description = "The default role to assume when running Terraform"
}

variable "management_role" {
  default     = "integrations-ci"
  type        = string
  description = "The role to assume when running Terraform for management resources"
}

variable "image_tag" {
  type        = string
  default     = "latest"
  description = "The tag of the image to deploy to Lambda"
}

variable "use_mock_sirius" {
  type        = bool
  default     = false
  description = "Whether to use the mock Sirius API"
}

variable "accounts" {
  type = map(
    object({
      name                 = string
      account_id           = string
      ual_account_id       = string
      force_destroy_bucket = bool
      is_production        = bool
      opg_hosted_zone      = string
      extra_allowed_roles  = list(string)
      vpc_id               = string
      secret_prefix        = string
      s3_vpc_endpoint_ids  = set(string)
    })
  )
  description = "A map of accounts to deploy to"
}

variable "environment_mapping" {
  type = map(string)
}
