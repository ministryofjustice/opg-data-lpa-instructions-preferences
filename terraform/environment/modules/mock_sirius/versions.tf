terraform {

  required_version = "<= 1.16.4"

  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = "~> 6.67.0"
      configuration_aliases = [aws, aws.management]
    }
  }
}
