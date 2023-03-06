resource "aws_security_group" "lpa_iap_mock_sirius" {
  name_prefix = "lpa-iap-mock-sirius-${terraform.workspace}-"
  vpc_id      = var.vpc_id
  description = "Mock Sirius LPA IaP ECS task"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(
    tomap({ "Name" : "lpa-iap-mock-sirius-${terraform.workspace}" })
  )
}

//RULES FOR APP ACCESS
data "aws_security_group" "lambda_api_ingress" {
  filter {
    name   = "tag:Name"
    values = ["integration-lambda-api-access-${var.target_environment}"]
  }
}

resource "aws_security_group_rule" "lambda_to_mock_sirius" {
  type                     = "ingress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  source_security_group_id = data.aws_security_group.lambda_api_ingress.id
  security_group_id        = aws_security_group.lpa_iap_mock_sirius.id
  description              = "LPA IaP Lambda to Mock Sirius"
}

//RULES FOR ENDPOINT ACCESS
data "aws_security_group" "vpc_endpoints" {
  tags   = { Name = "vpc-endpoint-access-private-subnets-eu-west-1" }
  vpc_id = var.vpc_id
}

resource "aws_security_group_rule" "etl_to_ecr_api_egress" {
  type                     = "egress"
  protocol                 = "tcp"
  from_port                = 443
  to_port                  = 443
  source_security_group_id = data.aws_security_group.vpc_endpoints.id
  security_group_id        = aws_security_group.lpa_iap_mock_sirius.id
  description              = "Outbound Mock Sirius to ECR API Endpoints SG"
}

//RULES FOR S3 ENDPOINT ACCESS
data "aws_vpc_endpoint" "s3_endpoint" {
  for_each     = var.s3_vpc_endpoint_ids
  service_name = "com.amazonaws.eu-west-1.s3"
  vpc_id       = var.vpc_id
  id           = each.value
}

resource "aws_security_group_rule" "etl_to_s3_egress" {
  type              = "egress"
  protocol          = "tcp"
  from_port         = 443
  to_port           = 443
  security_group_id = aws_security_group.lpa_iap_mock_sirius.id
  prefix_list_ids   = toset([for i in var.s3_vpc_endpoint_ids : data.aws_vpc_endpoint.s3_endpoint[i].prefix_list_id])
  description       = "Outbound Mock Sirius to S3 Endpoint"
}
