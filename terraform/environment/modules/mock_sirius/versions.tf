terraform {

  required_version = "<= 1.16.2"

  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = "~> 6.64.0"
      configuration_aliases = [aws, aws.management]
    }
  }
}
