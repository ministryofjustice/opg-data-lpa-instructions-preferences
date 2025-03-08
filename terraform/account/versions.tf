terraform {
  required_version = "<= 1.11.1"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.89.0"
    }
    pagerduty = {
      source  = "PagerDuty/pagerduty"
      version = "~> 3.21.0"
    }
  }
}
