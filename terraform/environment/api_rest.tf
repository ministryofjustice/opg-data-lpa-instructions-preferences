resource "aws_api_gateway_rest_api" "lpa_iap" {
  name        = "lpa-instructions-preferences-${local.environment}"
  description = "API Gateway for LPA instructions and preferences - ${local.environment}"
  body        = templatefile("../../docs/openapi/${local.api_name}.yml", local.api_template_vars)

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}
