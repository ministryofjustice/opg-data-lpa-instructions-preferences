resource "aws_cloudwatch_metric_alarm" "alarm" {
  actions_enabled     = var.alarm_actions_enabled
  alarm_name          = "${aws_sqs_queue.queue.name}-flood-alarm"
  alarm_description   = "The ${aws_sqs_queue.queue.name} main queue has a large number of queued items"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Average"
  threshold           = 2000
  treat_missing_data  = "notBreaching"
  alarm_actions       = [var.alarm_sns_topic_arn]
  dimensions = {
    "QueueName" = aws_sqs_queue.queue.name
  }
}

resource "aws_cloudwatch_metric_alarm" "deadletter_alarm" {
  actions_enabled     = var.alarm_actions_enabled
  alarm_name          = "${aws_sqs_queue.deadletter_queue.name}-not-empty-alarm"
  alarm_description   = "Items are on the ${aws_sqs_queue.deadletter_queue.name} queue"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Average"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [var.alarm_sns_topic_arn]
  dimensions = {
    "QueueName" = aws_sqs_queue.deadletter_queue.name
  }
}

resource "aws_cloudwatch_metric_alarm" "message_age_alarm" {
  actions_enabled           = var.alarm_actions_enabled
  alarm_name                = "${aws_sqs_queue.queue.name}-message-age-alarm"
  alarm_description         = "The queue ${aws_sqs_queue.queue.name} has unprocessed messages older than ${var.message_age_alarm_threshold} seconds"
  comparison_operator       = "GreaterThanThreshold"
  count                     = var.enable_message_age_alarm ? 1 : 0
  evaluation_periods        = 1
  insufficient_data_actions = []
  metric_name               = "ApproximateAgeOfOldestMessage"
  namespace                 = "AWS/SQS"
  period                    = 300
  statistic                 = "Minimum"
  threshold                 = var.message_age_alarm_threshold
  alarm_actions             = [var.alarm_sns_topic_arn]
  dimensions = {
    "QueueName" = aws_sqs_queue.queue.name
  }
}
