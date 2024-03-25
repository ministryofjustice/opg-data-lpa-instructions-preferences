terraform {

  required_version = "<= 1.7.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.42.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.11.0"
    }
  }
}
