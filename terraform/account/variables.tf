locals {
  environment = terraform.workspace
  account     = contains(keys(var.accounts), local.environment) ? var.accounts[local.environment] : var.accounts.development
}

variable "default_role" {
  default     = "integrations-ci"
  type        = string
  description = "Default role to assume when running Terraform"
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

variable "accounts" {
  type = map(
    object({
      name                 = string
      account_id           = string
      is_production        = bool
      pagerduty_service_id = string
    })
  )
}

variable "pagerduty_token" {
  type        = string
  description = "PagerDuty API token"
}
