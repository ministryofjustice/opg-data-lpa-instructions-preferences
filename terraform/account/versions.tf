terraform {
  required_version = "<= 1.8.3"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50.0"
    }
    pagerduty = {
      source  = "PagerDuty/pagerduty"
      version = "~> 3.12.0"
    }
  }
}
