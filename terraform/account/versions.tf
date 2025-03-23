terraform {
  required_version = "<= 1.11.2"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.92.0"
    }
    pagerduty = {
      source  = "PagerDuty/pagerduty"
      version = "~> 3.23.0"
    }
  }
}
