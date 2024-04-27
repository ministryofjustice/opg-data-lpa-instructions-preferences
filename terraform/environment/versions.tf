terraform {
  required_version = "<= 1.8.2"

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
