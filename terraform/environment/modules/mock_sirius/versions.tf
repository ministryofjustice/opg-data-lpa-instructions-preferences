terraform {

  required_version = "<= 1.8.3"

  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = "~> 5.50.0"
      configuration_aliases = [aws, aws.management]
    }
  }
}
