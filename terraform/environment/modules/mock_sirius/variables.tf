variable "vpc_id" {
  type = string
}
variable "environment" {
  type = string
}
variable "use_mock_sirius" {
  type = string
}
variable "subnets" {}
variable "image_tag" {
  type = string
}
variable "target_environment" {
  type = string
}
variable "s3_vpc_endpoint_ids" {}
