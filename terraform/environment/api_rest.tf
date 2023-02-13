data "template_file" "_" {
  template = local.openapi_spec
  vars     = local.api_template_vars
}

resource "aws_api_gateway_rest_api" "lpa_iap" {
  name        = "lpa-instructions-preferences-${local.environment}"
  description = "API Gateway for LPA instructions and preferences - ${local.environment}"
  body        = data.template_file._.rendered

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}
