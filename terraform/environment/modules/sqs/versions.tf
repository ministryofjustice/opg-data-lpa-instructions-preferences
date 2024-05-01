terraform {

  required_version = "<= 1.8.2"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.47.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.11.0"
    }
  }
}
