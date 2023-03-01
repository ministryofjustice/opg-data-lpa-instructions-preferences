locals {
  environment       = terraform.workspace
  account           = contains(keys(var.accounts), local.environment) ? var.accounts[local.environment] : var.accounts.development
  branch_build_flag = contains(keys(var.accounts), local.environment) ? false : true
  a_record          = local.branch_build_flag ? "${local.environment}.${data.aws_route53_zone.environment_cert.name}" : data.aws_route53_zone.environment_cert.name
  service           = "LPA Instructions and Preferences Integration"
  api_name          = "image-request-handler"
  openapi_spec      = file("../../docs/openapi/${local.api_name}.yml")

  expiration_days            = 365
  noncurrent_expiration_days = 30

  ual_api_task_env = local.account.name == "development" ? "demo" : local.account.name

  allowed_roles = tolist(concat(["arn:aws:iam::${local.account.ual_account_id}:role/${local.ual_api_task_env}-api-task-role"], local.account.extra_allowed_roles))

  api_template_vars = {
    region        = "eu-west-1"
    environment   = local.environment
    account_id    = local.account.account_id
    allowed_roles = join("\", \"", local.allowed_roles)
  }

  session_data = local.account.name == "development" ? "publicapi@opgtest.com" : "opg+publicapi@digital.justice.gov.uk"
}

variable "default_role" {
  default = "integrations-ci"
}

variable "management_role" {
  default = "integrations-ci"
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "use_mock_sirius" {
  type    = string
  default = "0"
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
      target_environment   = string
      s3_vpc_endpoint_ids  = set(string)
    })
  )
}
