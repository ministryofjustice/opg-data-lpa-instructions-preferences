locals {
  allowed_apigateway_arns = [
    "arn:aws:iam::${local.account.ual_account_id}:role/*-api-task-role",
    "arn:aws:iam::${local.account.account_id}:role/breakglass"
  ]
}

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

resource "aws_api_gateway_rest_api_policy" "lpa_iap" {
  rest_api_id = aws_api_gateway_rest_api.lpa_iap.id
  policy      = data.aws_iam_policy_document.api_invoke_aws_rest_api.json
}

data "aws_iam_policy_document" "api_invoke_aws_rest_api" {
  statement {
    sid    = "AllowInvokeOnAPIGateway"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = local.allowed_apigateway_arns
    }

    actions = [
      "execute-api:Invoke"
    ]

    resources = ["${aws_api_gateway_rest_api.lpa_iap.execution_arn}/*"]
  }
}