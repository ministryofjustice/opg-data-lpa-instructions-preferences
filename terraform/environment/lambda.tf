data "aws_ecr_repository" "lpa_iap_request_handler" {
  provider = aws.management
  name     = "integrations/lpa-iap-request-handler-lambda"
}

//Modify here for new version
module "request_handler_lamdba" {
  source            = "./modules/lambda"
  lambda_name       = "lpa-iap-request-handler-${local.environment}"
  description       = "Function to return signed urls and kick off iap processing"
  working_directory = "/var/task"
  environment_variables = {
    ENVIRONMENT          = local.environment
  }
  image_uri          = "${data.aws_ecr_repository.lpa_iap_request_handler.repository_url}:${var.image_tag}"
  ecr_arn            = data.aws_ecr_repository.lpa_iap_request_handler.arn
  account            = local.account
  environment        = local.environment
  rest_api           = aws_api_gateway_rest_api.lpa_iap
  aws_subnet_ids     = []
  logs_kms_key       = data.aws_kms_key.lpa_iap_logs
  retention_in_days  = 365
}

# Needed for next lambda
data "aws_security_group" "lambda_api_ingress" {
  filter {
    name   = "tag:Name"
    values = ["integration-lambda-api-access-${local.account.target_environment}"]
  }
}
