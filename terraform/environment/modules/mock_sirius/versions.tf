terraform {

  required_version = "<= 1.10.5"

  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = "~> 5.86.0"
      configuration_aliases = [aws, aws.management]
    }
  }
}
