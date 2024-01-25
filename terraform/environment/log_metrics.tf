data "aws_sns_topic" "cloudwatch_to_pagerduty" {
  name = "CloudWatch-to-PagerDuty-${local.account.name}-InstructionsAndPreferences"
}

resource "aws_cloudwatch_log_metric_filter" "pdf_sizes_bytes" {
  name           = "PDF Sizes (Bytes)"
  pattern        = "{ $.pdfSize = \"*\" }"
  log_group_name = module.processor_lamdba.lambda_log.name

  metric_transformation {
    name      = "PDFSize"
    namespace = "IaP/PDFStatistics"
    value     = "$.pdfSize"
    unit      = "Bytes"
    dimensions = {
      pdfSize = "$.pdfSize"
    }
  }
}


resource "aws_cloudwatch_log_metric_filter" "pdf_length_pages" {
  name           = "PDF Length (Pages)"
  pattern        = "{ $.pdfLength = \"*\" }"
  log_group_name = module.processor_lamdba.lambda_log.name

  metric_transformation {
    name      = "PDFLength"
    namespace = "IaP/PDFStatistics"
    value     = "$.pdfLength"
    dimensions = {
      pdfLength = "$.pdfLength"
    }

  }
}

resource "aws_cloudwatch_log_metric_filter" "image_processor_error_count" {
  name           = "ImageProcessorErrorCount"
  pattern        = "{ $.status = \"Error\" }"
  log_group_name = module.processor_lamdba.lambda_log.name

  metric_transformation {
    name      = "ErrorCount"
    namespace = "IaP/Stats"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "iap_error_count" {
  alarm_name          = "${local.environment}-IAP-Error-Count"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = aws_cloudwatch_log_metric_filter.image_processor_error_count.metric_transformation[0].name
  namespace           = aws_cloudwatch_log_metric_filter.image_processor_error_count.metric_transformation[0].namespace
  period              = "300"
  statistic           = "Sum"
  threshold           = "3"
  alarm_description   = "This alarm is triggered when there are more than 3 IAP errors in a 5 minute period."
  alarm_actions       = [data.aws_sns_topic.cloudwatch_to_pagerduty.arn]
  treat_missing_data  = "notBreaching"
}
