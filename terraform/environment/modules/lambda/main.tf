resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.lambda_name}"
  kms_key_id        = var.logs_kms_key.arn
  retention_in_days = var.retention_in_days
}

resource "aws_lambda_function" "lambda_function" {
  function_name = var.lambda_name
  image_uri     = var.image_uri
  package_type  = var.package_type
  role          = aws_iam_role.lambda_role.arn
  timeout       = var.timeout
  memory_size   = var.memory
  depends_on    = [aws_cloudwatch_log_group.lambda]

  vpc_config {
    subnet_ids         = var.aws_subnet_ids
    security_group_ids = var.security_group_ids
  }

  tracing_config {
    mode = "Active"
  }

  ephemeral_storage {
    size = var.ephemeral_storage
  }

  dynamic "environment" {
    for_each = length(keys(var.environment_variables)) == 0 ? [] : [true]
    content {
      variables = var.environment_variables
    }
  }
}

resource "aws_lambda_permission" "lambda_permission" {
  count         = var.rest_api == null ? 0 : 1
  statement_id  = "AllowApiLpaIapGatewayInvoke_${var.environment}_${var.api_version}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_function.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${var.rest_api.execution_arn}/*/*/*"
}
