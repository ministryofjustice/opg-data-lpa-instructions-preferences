data "pagerduty_vendor" "cloudwatch" {
  name = "Cloudwatch"
}

resource "aws_sns_topic_subscription" "cloudwatch_sns_subscription" {
  topic_arn              = aws_sns_topic.cloudwatch_to_pagerduty.arn
  protocol               = "https"
  endpoint_auto_confirms = true
  endpoint               = "https://events.pagerduty.com/integration/${pagerduty_service_integration.cloudwatch_integration.integration_key}/enqueue"
}

resource "aws_sns_topic" "cloudwatch_to_pagerduty" {
  name              = "CloudWatch-to-PagerDuty-${terraform.workspace}-InstructionsAndPreferences"
  kms_master_key_id = aws_kms_key.sns.key_id
}

resource "pagerduty_service_integration" "cloudwatch_integration" {
  name    = "${data.pagerduty_vendor.cloudwatch.name} ${terraform.workspace} Environment"
  service = local.account.pagerduty_service_id
  vendor  = data.pagerduty_vendor.cloudwatch.id
}

resource "aws_sns_topic_policy" "cloudwatch_to_pagerduty" {
  arn    = aws_sns_topic.cloudwatch_to_pagerduty.arn
  policy = data.aws_iam_policy_document.cloudwatch_to_pagerduty.json
}

data "aws_iam_policy_document" "cloudwatch_to_pagerduty" {
  statement {
    sid = "AllowCloudWatchToPublishToSNS"
    actions = [
      "sns:Publish",
    ]

    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com"]
    }

    resources = [
      aws_sns_topic.cloudwatch_to_pagerduty.arn,
    ]
  }
}
