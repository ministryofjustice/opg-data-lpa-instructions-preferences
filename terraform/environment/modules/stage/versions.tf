terraform {

  required_version = "<= 1.11.1"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.89.0"
    }
    time = {
      source  = "hashicorp/time"
      version = ">= 0.10.0"
    }
    local = {
      source  = "hashicorp/local"
      version = ">= 2.4.0"
    }
  }
}
