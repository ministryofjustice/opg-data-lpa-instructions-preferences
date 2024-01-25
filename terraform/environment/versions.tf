terraform {
  required_version = "<= 1.6.3"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.24.0"
    }
    pagerduty = {
      source  = "PagerDuty/pagerduty"
      version = "~> 3.3.0"
    }
  }
}
