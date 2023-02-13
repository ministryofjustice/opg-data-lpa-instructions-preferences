locals {
  certificate_arn = local.branch_build_flag ? data.aws_acm_certificate.environment_cert[0].arn : aws_acm_certificate.environment_cert[0].arn
  certificate     = local.branch_build_flag ? data.aws_acm_certificate.environment_cert[0] : aws_acm_certificate.environment_cert[0]
}

resource "aws_api_gateway_method_settings" "global_gateway_settings" {
  rest_api_id = aws_api_gateway_rest_api.lpa_iap.id
  //Modify here for new version
  stage_name  = module.deploy_v1.stage.stage_name
  method_path = "*/*"

  settings {
    metrics_enabled = true
    logging_level   = "INFO"
  }
}

resource "aws_api_gateway_domain_name" "lpa_iap" {
  domain_name              = trimsuffix(local.a_record, ".")
  regional_certificate_arn = local.certificate_arn
  security_policy          = "TLS_1_2"

  depends_on = [local.certificate]
  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

module "deploy_v1" {
  source             = "./modules/stage"
  account_name       = local.account.name
  api_name           = local.api_name
  aws_subnet_ids     = data.aws_subnets.private.ids
  domain_name        = aws_api_gateway_domain_name.lpa_iap
  environment        = local.environment
  openapi_version    = "v1"
  region_name        = data.aws_region.region.name
  rest_api           = aws_api_gateway_rest_api.lpa_iap
  lambda             = module.request_handler_lamdba.lambda
  logs_kms_key       = data.aws_kms_key.lpa_iap_logs
  image_tag = var.image_tag
}

//Modify here for new version
resource "aws_api_gateway_base_path_mapping" "mapping_v1" {
  api_id      = aws_api_gateway_rest_api.lpa_iap.id
  stage_name  = module.deploy_v1.deployment.stage_name
  domain_name = aws_api_gateway_domain_name.lpa_iap.domain_name
  base_path   = module.deploy_v1.deployment.stage_name
}
