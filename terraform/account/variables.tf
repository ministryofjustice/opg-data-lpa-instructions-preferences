locals {
  environment = terraform.workspace
  account     = contains(keys(var.accounts), local.environment) ? var.accounts[local.environment] : var.accounts.development
}

variable "default_role" {
  default = "integrations-ci"
}

variable "local_environment" {

}

variable "accounts" {
  type = map(
    object({
      name = string
      account_id           = string
    })
  )
}
