terraform {
  required_version = "<= 1.10.2"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.81.0"
    }
    pagerduty = {
      source  = "PagerDuty/pagerduty"
      version = "~> 3.18.0"
    }
  }
}
