module "iap_queues" {
  source                      = "./modules/sqs"
  name                        = "${local.environment}-lpa-iap-requests"
  alarm_actions_enabled       = false
  alarm_sns_topic_arn         = ""
  allowed_arn_list            = [module.request_handler_lamdba.lambda_execution_role.arn]
  visibility_timeout_seconds  = 300
  enable_message_age_alarm    = true
  message_age_alarm_threshold = 86400
  fifo_queue                  = false
  content_based_deduplication = false
  providers = {
    aws = aws
  }
}

resource "aws_lambda_event_source_mapping" "lpa_iap_processor" {
  event_source_arn  = module.iap_queues.queue.arn
  function_name     = module.processor_lamdba.lambda.function_name
  starting_position = "LATEST"
}
