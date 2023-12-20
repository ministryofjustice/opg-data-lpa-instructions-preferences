# PagerDuty CloudWatch Integration and Alarm

data "pagerduty_vendor" "cloudwatch" {
  name = "Cloudwatch"
}

resource "pagerduty_service_integration" "cloudwatch_integration" {
  name    = "${data.pagerduty_vendor.cloudwatch.name} ${local.environment} Environment"
  service = local.account.pagerduty_service_id
  vendor  = data.pagerduty_vendor.cloudwatch.id
}

resource "aws_sns_topic_subscription" "cloudwatch_sns_subscription" {
  topic_arn              = aws_sns_topic.cloudwatch_to_pagerduty.arn
  protocol               = "https"
  endpoint_auto_confirms = true
  endpoint               = "https://events.pagerduty.com/integration/${pagerduty_service_integration.cloudwatch_integration.integration_key}/enqueue"
}

resource "aws_sns_topic" "cloudwatch_to_pagerduty" {
  name              = "CloudWatch-to-PagerDuty-${local.environment}-InstructionsAndPreferences"
  kms_master_key_id = data.aws_kms_key.lpa_iap_sns.key_id
}

resource "aws_cloudwatch_metric_alarm" "metric" {
  alarm_name          = "Excessive Errors for IAP"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = aws_cloudwatch_log_metric_filter.image_processor_error_count.metric_transformation[0].name
  namespace           = aws_cloudwatch_log_metric_filter.image_processor_error_count.metric_transformation[0].namespace
  period              = "300"
  statistic           = "Sum"
  threshold           = "3"
  alarm_description   = "This alarm is triggered when there are more than 3 IAP errors in a 5 minute period."
  alarm_actions       = ["${aws_sns_topic.cloudwatch_to_pagerduty.arn}"]
  treat_missing_data  = "notBreaching"
}
