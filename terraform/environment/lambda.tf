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
    ENVIRONMENT  = local.environment
    VERSION      = "v1"
    LOGGER_LEVEL = "INFO"
  }
  image_uri         = "${data.aws_ecr_repository.lpa_iap_request_handler.repository_url}:${var.image_tag}"
  ecr_arn           = data.aws_ecr_repository.lpa_iap_request_handler.arn
  account           = local.account
  environment       = local.environment
  rest_api          = aws_api_gateway_rest_api.lpa_iap
  aws_subnet_ids    = []
  logs_kms_key      = data.aws_kms_key.lpa_iap_logs
  retention_in_days = 365
}

data "aws_ecr_repository" "lpa_iap_processor" {
  provider = aws.management
  name     = "integrations/lpa-iap-scan-processor-lambda"
}

module "processor_lamdba" {
  source            = "./modules/lambda"
  lambda_name       = "lpa-iap-processor-${local.environment}"
  description       = "Function to process scanned documents and extract instructions and preferences"
  working_directory = "/var/task"
  environment_variables = {
    ENVIRONMENT        = local.environment
    SIRIUS_URL         = var.use_mock_sirius == "1" ? "http://mock-sirius.lpa-iap-${local.environment}.ecs" : "http://api.${local.account.target_environment}.ecs"
    SESSION_DATA       = local.session_data
    TARGET_ENVIRONMENT = local.account.target_environment
    SECRET_PREFIX      = local.account.secret_prefix
    SIRIUS_URL_PART    = "/api/public/v1"
    LOGGER_LEVEL       = "DEBUG"
  }
  image_uri          = "${data.aws_ecr_repository.lpa_iap_processor.repository_url}:${var.image_tag}"
  ecr_arn            = data.aws_ecr_repository.lpa_iap_request_handler.arn
  account            = local.account
  environment        = local.environment
  timeout            = 600
  memory             = 8192
  aws_subnet_ids     = data.aws_subnets.private.ids
  security_group_ids = [data.aws_security_group.lambda_api_ingress.id]
  logs_kms_key       = data.aws_kms_key.lpa_iap_logs
  retention_in_days  = 365
  ephemeral_storage  = 2048
}

# Needed for next lambda
data "aws_security_group" "lambda_api_ingress" {
  filter {
    name   = "tag:Name"
    values = ["integration-lambda-api-access-${local.account.target_environment}"]
  }
}
