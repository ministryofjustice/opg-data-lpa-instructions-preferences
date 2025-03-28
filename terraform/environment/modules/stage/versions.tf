terraform {

  required_version = "<= 1.9.2"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.58.0"
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
