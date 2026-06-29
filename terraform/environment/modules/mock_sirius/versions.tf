terraform {

  required_version = "<= 1.15.6"

  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = "~> 6.51.0"
      configuration_aliases = [aws, aws.management]
    }
  }
}
