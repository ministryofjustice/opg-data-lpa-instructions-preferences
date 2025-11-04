terraform {
  required_version = "<= 1.13.4"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.100.0"
    }
    pagerduty = {
      source  = "PagerDuty/pagerduty"
      version = "~> 3.30.0"
    }
  }
}
