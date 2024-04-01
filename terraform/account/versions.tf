terraform {
  required_version = "<= 1.7.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.43.0"
    }
    pagerduty = {
      source  = "PagerDuty/pagerduty"
      version = "~> 3.10.0"
    }
  }
}
