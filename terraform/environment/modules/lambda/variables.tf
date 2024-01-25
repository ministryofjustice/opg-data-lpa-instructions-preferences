variable "environment" {
  description = "The environment lambda is being deployed to."
  type        = string
}

variable "aws_subnet_ids" {
  description = "A list of subnet ids for vpc connectivity."
  type        = list(string)
}

variable "tags" {
  description = "A map of tags to use."
  type        = map(string)
  default     = {}
}

variable "security_group_ids" {
  description = "Security groups to use"
  type        = list(string)
  default     = []
}

variable "rest_api" {
  default     = null
  description = "Object containing the REST API"
  type = object({
    execution_arn = string
  })
}

variable "memory" {
  description = "The memory to use."
  type        = number
  default     = 1024
}

variable "image_uri" {
  description = "The image uri in ECR."
  type        = string
  default     = null
}

variable "ecr_arn" {
  description = "The ECR arn for lambda image."
  type        = string
  default     = null
}

variable "environment_variables" {
  description = "A map that defines environment variables for the Lambda Function."
  type        = map(string)
  default     = {}
}

variable "lambda_name" {
  description = "A unique name for your Lambda Function"
  type        = string
}

variable "package_type" {
  description = "The Lambda deployment package type."
  type        = string
  default     = "Image"
}

variable "timeout" {
  description = "The amount of time your Lambda Function has to run in seconds."
  type        = number
  default     = 30
}

variable "api_version" {
  description = "The version deployed."
  type        = string
  default     = "v1"
}

variable "logs_kms_key" {
  description = "Object containing the KMS key for encrypting the logs"
  type = object({
    arn = string
  })
}

variable "retention_in_days" {
  description = "Log retention in days"
  type        = number
}

variable "ephemeral_storage" {
  description = "The amount of Ephemeral storage (/tmp) to allocate for the Lambda Function in MB"
  type        = number
  default     = 512
}
