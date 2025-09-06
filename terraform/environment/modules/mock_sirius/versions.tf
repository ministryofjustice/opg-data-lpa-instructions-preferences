terraform {

  required_version = "<= 1.13.1"

  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = "~> 5.100.0"
      configuration_aliases = [aws, aws.management]
    }
  }
}
