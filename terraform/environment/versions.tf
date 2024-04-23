terraform {
  required_version = "<= 1.8.1"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.46.0"
    }
    pagerduty = {
      source  = "PagerDuty/pagerduty"
      version = "~> 3.11.0"
    }
  }
}
