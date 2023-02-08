locals {
  environment = terraform.workspace
  account     = contains(keys(var.accounts), local.environment) ? var.accounts[local.environment] : var.accounts.development

  expiration_days            = 365
  noncurrent_expiration_days = 30
}
variable "default_role" {
  default = "integrations-ci"
}

variable "accounts" {
  type = map(
    object({
      name                 = string
      account_id           = string
      force_destroy_bucket = bool
      is_production        = bool
    })
  )
}
