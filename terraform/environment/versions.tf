terraform {
  required_version = "<= 1.16.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.67.0"
    }
    pagerduty = {
      source  = "PagerDuty/pagerduty"
      version = "~> 3.36.0"
    }
  }
}
