module "mock_sirius" {
  count               = contains(keys(var.accounts), local.environment) && local.environment != "development" ? 0 : 1
  source              = "./modules/mock_sirius"
  vpc_id              = local.account.vpc_id
  environment         = local.environment
  use_mock_sirius     = var.use_mock_sirius
  subnets             = data.aws_subnets.private.ids
  image_tag           = var.image_tag
  target_environment  = local.target_environment
  s3_vpc_endpoint_ids = local.account.s3_vpc_endpoint_ids
  providers = {
    aws            = aws,
    aws.management = aws.management
  }
}
