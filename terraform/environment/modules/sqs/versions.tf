terraform {

  required_version = "<= 1.17.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.70.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.14.0"
    }
  }
}
