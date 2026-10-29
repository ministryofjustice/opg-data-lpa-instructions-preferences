terraform {

  required_version = "<= 1.17.0"

  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = "~> 6.69.0"
      configuration_aliases = [aws, aws.management]
    }
  }
}
