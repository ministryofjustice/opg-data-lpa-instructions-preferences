terraform {
  required_version = "<= 1.11.4"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.94.0"
    }
    pagerduty = {
      source  = "PagerDuty/pagerduty"
      version = "~> 3.24.0"
    }
  }
}
