variable "account_name" {
  description = "Account name to use"
}

variable "api_name" {
  description = "Name fo the API gateway"
  type        = string
}

variable "aws_subnet_ids" {
  description = "List of subnets"
  type        = list(string)
}

variable "domain_name" {
  description = "Domain name to use"
}
variable "environment" {
  type = string
}

variable "lambda" {
  description = "Lambda to use"
}

variable "openapi_version" {
  description = "Openapi version"
}

variable "region_name" {
  description = "Region name"
}

variable "rest_api" {
  description = "The rest API"
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "logs_kms_key" {
  description = "KMS key for encrypting the logs"
}
