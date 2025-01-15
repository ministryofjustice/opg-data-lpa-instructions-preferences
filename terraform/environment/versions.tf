terraform {
  required_version = "<= 1.10.4"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.83.0"
    }
    pagerduty = {
      source  = "PagerDuty/pagerduty"
      version = "~> 3.19.0"
    }
  }
}
