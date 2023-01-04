terraform {

  backend "s3" {
    bucket         = "opg.terraform.state"
    key            = "github-workflow-example-account/terraform.tfstate"
    encrypt        = true
    region         = "eu-west-1"
    role_arn       = "arn:aws:iam::311462405659:role/gh-workflow-example-ci"
    dynamodb_table = "remote_lock"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "3.40.0"
    }
  }
  required_version = ">= 1.1.0"
}

locals {
  sandbox = "995199299616"
}

provider "aws" {
  alias = "sandbox"

  assume_role {
    role_arn     = "arn:aws:iam::${local.sandbox}:role/${var.DEFAULT_ROLE}"
    session_name = "terraform-session"
  }
}

variable "DEFAULT_ROLE" {
  default = "integrations-ci"
}

data "aws_caller_identity" "current" {
  provider = aws.sandbox
}
