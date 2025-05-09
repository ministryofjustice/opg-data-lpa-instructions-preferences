terraform {

  backend "s3" {
    bucket         = "opg.terraform.state"
    key            = "opg-data-lpa-instructions-preferences/terraform.tfstate"
    encrypt        = true
    region         = "eu-west-1"
    role_arn       = "arn:aws:iam::311462405659:role/integrations-ci"
    dynamodb_table = "remote_lock"
  }
}

locals {
  tags = {
    business-unit          = "OPG"
    application            = "LPA-Instructions-and-Preferences"
    environment-name       = local.environment
    owner                  = "OPG Supervision"
    infrastructure-support = "OPG WebOps: opgteam@digital.justice.gov.uk"
    is-production          = local.account.is_production
    source-code            = "https://github.com/ministryofjustice/opg-data-lpa-instructions-preferences"
  }
}

provider "aws" {
  region = "eu-west-1"
  default_tags {
    tags = local.tags
  }
  assume_role {
    role_arn     = "arn:aws:iam::${local.account.account_id}:role/${var.default_role}"
    session_name = "terraform-session"
  }
}

provider "aws" {
  region = "eu-west-1"
  alias  = "management"
  assume_role {
    role_arn     = "arn:aws:iam::311462405659:role/${var.management_role}"
    session_name = "terraform-session"
  }
  default_tags {
    tags = local.tags
  }
}
