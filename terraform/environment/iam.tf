data "aws_secretsmanager_secret" "jwt_key" {
  name = join("/", compact([local.account.secret_prefix, "jwt-key"]))
}

//===============Related to Request Handler Lambda Task Execution Role===================
resource "aws_iam_policy" "ual_iap_request_handler_lambda_execution" {
  name   = "lpa-iap-request-handler-${local.environment}"
  policy = data.aws_iam_policy_document.ual_iap_request_handler_lambda.json
}

resource "aws_iam_role_policy_attachment" "ual_iap_request_handler_lambda_attachment" {
  role       = module.request_handler_lamdba.lambda_execution_role.id
  policy_arn = aws_iam_policy.ual_iap_request_handler_lambda_execution.arn
}

// Access policy for the s3 bucket
data "aws_iam_policy_document" "ual_iap_request_handler_lambda" {
  #tfsec:ignore:aws-iam-no-policy-wildcards - this is not overly permissive
  statement {
    sid       = "AllowS3Actions"
    effect    = "Allow"
    resources = [module.ual_iap_s3.arn, "${module.ual_iap_s3.arn}/*"]
    actions   = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
  }

  statement {
    sid       = "AllowKms"
    effect    = "Allow"
    resources = [module.ual_iap_s3.arn]
    actions = [
      "kms:Decrypt",
      "kms:GenerateDataKey",
    ]
  }
}

//===============Related to Processor Lambda Task Execution Role===================

resource "aws_iam_policy" "ual_iap_processor_lambda_execution" {
  name   = "lpa-iap-processor-${local.environment}"
  policy = data.aws_iam_policy_document.ual_iap_processor_lambda.json
}

resource "aws_iam_role_policy_attachment" "ual_iap_processor_lambda_attachment" {
  role       = module.processor_lamdba.lambda_execution_role.id
  policy_arn = aws_iam_policy.ual_iap_processor_lambda_execution.arn
}

data "aws_s3_bucket" "sirius" {
  bucket = "opg-backoffice-datastore-${local.account.target_environment}"
}

// Access policy for the both s3 buckets and the SQS queue
data "aws_iam_policy_document" "ual_iap_processor_lambda" {
  #tfsec:ignore:aws-iam-no-policy-wildcards - this is not overly permissive
  statement {
    sid       = "AllowS3PutInBucket"
    effect    = "Allow"
    resources = [module.ual_iap_s3.arn, "${module.ual_iap_s3.arn}/*"]
    actions   = ["s3:PutObject", "s3:ListBucket"]
  }

  #tfsec:ignore:aws-iam-no-policy-wildcards - this is not overly permissive
  statement {
    sid       = "AllowS3GetInBucket"
    effect    = "Allow"
    resources = [data.aws_s3_bucket.sirius.arn, "${data.aws_s3_bucket.sirius.arn}/*"]
    actions   = ["s3:GetObject", "s3:ListBucket"]
  }

  statement {
    sid       = "AllowSQSReceiveMessage"
    effect    = "Allow"
    resources = [module.iap_queues.queue.arn, module.iap_queues.deadletter_queue.arn]
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:ListQueueTags",
      "sqs:ChangeMessageVisibility",
      "sqs:GetQueueUrl",
      "sqs:PurgeQueue"
    ]
  }

  statement {
    sid       = "AllowGetSecretValue"
    effect    = "Allow"
    resources = [data.aws_secretsmanager_secret.jwt_key.arn]
    actions = [
      "secretsmanager:GetSecretValue"
    ]
  }

  statement {
    sid    = "AllowKms"
    effect = "Allow"
    resources = [
      module.ual_iap_s3.arn,
      data.aws_s3_bucket.sirius.arn,
      module.iap_queues.queue.arn,
      module.iap_queues.deadletter_queue.arn
    ]
    actions = [
      "kms:Decrypt",
      "kms:GenerateDataKey",
    ]
  }
}
