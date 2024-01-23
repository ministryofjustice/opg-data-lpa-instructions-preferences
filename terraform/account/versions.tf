terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
    pagerduty = {
      source  = "PagerDuty/pagerduty"
      version = "~> 3.4.0"
    }
  }
}
