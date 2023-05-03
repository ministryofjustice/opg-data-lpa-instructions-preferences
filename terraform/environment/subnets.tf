data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [local.account.vpc_id]
  }
  tags = {
    Name = "private*"
  }
}

data "aws_region" "region" {}
