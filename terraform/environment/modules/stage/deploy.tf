locals {
  openapi_sha = substr(replace(base64sha256(data.local_file.openapispec.content_base64), "/[^0-9A-Za-z_]/", ""), 0, 5)
}

data "local_file" "openapispec" {
  filename = "../../docs/openapi/${var.api_name}.yml"
}

resource "aws_api_gateway_deployment" "deploy" {
  rest_api_id = var.rest_api.id
  variables = {
    // Force a deploy on when content has changed
    stage_version   = var.openapi_version
    content_api_sha = local.openapi_sha
    lambda_version  = var.image_tag
  }
  lifecycle {
    create_before_destroy = true
  }
}
