terraform {
  required_version = "<= 1.7.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.44.0"
    }
    pagerduty = {
      source  = "PagerDuty/pagerduty"
      version = "~> 3.11.0"
    }
  }
}
