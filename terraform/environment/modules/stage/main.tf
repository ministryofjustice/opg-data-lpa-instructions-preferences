locals {
  //Modify here for new version
  v1 = {
    app_name : var.lambda.function_name
  }
  stage_vars = local.v1
}

resource "aws_api_gateway_stage" "currentstage" {
  stage_name           = var.openapi_version
  depends_on           = [aws_cloudwatch_log_group.lpa_iap]
  rest_api_id          = var.rest_api.id
  deployment_id        = aws_api_gateway_deployment.deploy.id
  xray_tracing_enabled = false
  //Modify here for new version
  variables = local.stage_vars

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.lpa_iap.arn
    format = join("", [
      "{\"requestId\":\"$context.requestId\",",
      "\"ip\":\"$context.identity.sourceIp\",",
      "\"caller\":\"$context.identity.caller\",",
      "\"user\":\"$context.identity.user\",",
      "\"requestTime\":\"$context.requestTime\",",
      "\"httpMethod\":\"$context.httpMethod\",",
      "\"resourcePath\":\"$context.resourcePath\",",
      "\"status\":\"$context.status\",",
      "\"protocol\":\"$context.protocol\",",
      "\"responseLength\":\"$context.responseLength\"}"
    ])
  }
}

resource "aws_cloudwatch_log_group" "lpa_iap" {
  name              = "API-Gateway-Execution-Logs-${var.rest_api.name}"
  kms_key_id        = var.logs_kms_key.arn
  retention_in_days = 30
}


data "aws_wafv2_web_acl" "integrations" {
  name  = "integrations-${var.account_name}-${var.region_name}-web-acl"
  scope = "REGIONAL"
}

resource "aws_wafv2_web_acl_association" "api_gateway_stage" {
  resource_arn = aws_api_gateway_stage.currentstage.arn
  web_acl_arn  = data.aws_wafv2_web_acl.integrations.arn
}
