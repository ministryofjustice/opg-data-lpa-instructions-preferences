locals {
  environment = terraform.workspace
  account     = contains(keys(var.accounts), local.environment) ? var.accounts[local.environment] : var.accounts.development
}

variable "default_role" {
  default = "integrations-ci"
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

provider "pagerduty" {
  token = var.pagerduty_token
}
