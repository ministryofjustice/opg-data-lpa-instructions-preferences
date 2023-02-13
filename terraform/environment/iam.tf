//===============Related to Lambda Task Execution Role===================
resource "aws_iam_policy" "ual_iap_lambda_execution" {
  name   = "ual-iap-s3-${local.environment}"
  policy = data.aws_iam_policy_document.ual_iap_lambda.json
}

resource "aws_iam_role_policy_attachment" "ual_iap_lambda_attachment" {
  role       = module.request_handler_lamdba.lambda_execution_role.id
  policy_arn = aws_iam_policy.ual_iap_lambda_execution.arn
}

// Access policy for the s3 bucket
data "aws_iam_policy_document" "ual_iap_lambda" {
  statement {
    sid       = "AllowS3ListBucket"
    effect    = "Allow"
    resources = [module.ual_iap_s3.arn]
    actions   = ["s3:ListBucket"]
  }

  #tfsec:ignore:aws-iam-no-policy-wildcards - this is not overly permissive
  statement {
    sid       = "AllowS3ActionsInBucket"
    effect    = "Allow"
    resources = ["${module.ual_iap_s3.arn}/*"]
    actions   = ["s3:PutObject", "s3:GetObject"]
  }

  statement {
    sid    = "AllowKms"
    effect = "Allow"
    resources = [module.ual_iap_s3.arn]
    actions = [
      "kms:Decrypt",
      "kms:GenerateDataKey",
    ]
  }
}
