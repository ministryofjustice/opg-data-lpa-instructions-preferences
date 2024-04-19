terraform {
  required_version = "<= 1.8.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.45.0"
    }
    pagerduty = {
      source  = "PagerDuty/pagerduty"
      version = "~> 3.11.0"
    }
  }
}
