variable "vpc_id" {
  type        = string
  description = "The VPC ID"
}

variable "environment" {
  type        = string
  description = "The environment name"
}

variable "use_mock_sirius" {
  type        = bool
  description = "Whether to use the mock sirius"
}

variable "subnets" {
  type        = list(string)
  description = "List of subnets to deploy mock Sirius to"
}

variable "image_tag" {
  type        = string
  description = "The image tag to use for the mock sirius"
}

variable "target_environment" {
  type        = string
  description = "The name of the environment that will be connecting to the mock sirius"
}

variable "s3_vpc_endpoint_ids" {
  type        = list(string)
  description = "List of S3 VPC endpoint IDs"
}
