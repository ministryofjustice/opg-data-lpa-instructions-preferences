resource "aws_sqs_queue" "queue" {
  name                              = "${var.name}${var.fifo_queue == true ? ".fifo" : ""}"
  message_retention_seconds         = var.message_retention_seconds
  visibility_timeout_seconds        = var.visibility_timeout_seconds
  fifo_queue                        = var.fifo_queue
  content_based_deduplication       = var.content_based_deduplication
  kms_master_key_id                 = var.kms_master_key_id
  kms_data_key_reuse_period_seconds = var.kms_data_key_reuse_period_seconds
  max_message_size                  = var.max_message_size
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.deadletter_queue.arn,
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue_policy" "queue" {
  queue_url  = aws_sqs_queue.queue.id
  policy     = data.aws_iam_policy_document.queue.json
  depends_on = [time_sleep.wait_60_seconds]
}

data "aws_iam_policy_document" "queue" {
  statement {
    effect    = "Allow"
    resources = [aws_sqs_queue.queue.arn]
    actions = [
      "sqs:ChangeMessageVisibility",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ListQueueTags",
      "sqs:ReceiveMessage",
      "sqs:SendMessage",
    ]
    principals {
      type        = "AWS"
      identifiers = tolist(var.allowed_arn_list)
    }
  }
}

resource "aws_sqs_queue" "deadletter_queue" {
  name                              = "${var.name}-dead-letter-queue${var.fifo_queue == true ? ".fifo" : ""}"
  message_retention_seconds         = var.message_retention_seconds
  visibility_timeout_seconds        = var.visibility_timeout_seconds
  fifo_queue                        = var.fifo_queue
  content_based_deduplication       = var.content_based_deduplication
  kms_master_key_id                 = var.kms_master_key_id
  kms_data_key_reuse_period_seconds = var.kms_data_key_reuse_period_seconds
  max_message_size                  = var.max_message_size
}

resource "aws_sqs_queue_policy" "deadletter_queue" {
  queue_url  = aws_sqs_queue.deadletter_queue.id
  policy     = data.aws_iam_policy_document.deadletter_queue.json
  depends_on = [time_sleep.wait_60_seconds]
}

data "aws_iam_policy_document" "deadletter_queue" {
  statement {
    effect    = "Allow"
    resources = [aws_sqs_queue.deadletter_queue.arn]
    actions = [
      "sqs:ChangeMessageVisibility",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ListQueueTags",
      "sqs:ReceiveMessage",
      "sqs:SendMessage",
    ]
    principals {
      type        = "AWS"
      identifiers = tolist(var.allowed_arn_list)
    }
  }
}

resource "time_sleep" "wait_60_seconds" {
  depends_on = [
    aws_sqs_queue.queue,
    aws_sqs_queue.deadletter_queue
  ]

  create_duration = "60s"
}
