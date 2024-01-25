variable "account_name" {
  description = "Account name to use"
  type        = string
}

variable "api_name" {
  description = "Name fo the API gateway"
  type        = string
}

variable "lambda" {
  description = "Object containing the lambda function to use"
  type = object({
    function_name = string
  })
}

variable "openapi_version" {
  description = "Openapi version"
  type        = string
  default     = "v1"
}

variable "region_name" {
  description = "Region name"
  type        = string
}

variable "rest_api" {
  description = "Object containing the REST API to use"
  type = object({
    id   = string
    name = string
  })
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "logs_kms_key" {
  description = "Object containing the KMS key for encrypting the logs"
  type = object({
    arn = string
  })
}
