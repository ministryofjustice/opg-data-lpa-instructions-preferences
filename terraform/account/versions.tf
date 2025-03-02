terraform {
  required_version = "<= 1.11.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.88.0"
    }
    pagerduty = {
      source  = "PagerDuty/pagerduty"
      version = "~> 3.21.0"
    }
  }
}
