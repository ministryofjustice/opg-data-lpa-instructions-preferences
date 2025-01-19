terraform {

  required_version = "<= 1.10.4"

  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = "~> 5.84.0"
      configuration_aliases = [aws, aws.management]
    }
  }
}
