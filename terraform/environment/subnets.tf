data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [local.account.vpc_id]
  }

  filter {
    name = "tag:Name"
    values = [
      "application-*",
      "private-*"
    ]
  }
}

data "aws_region" "region" {}
