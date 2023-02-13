//===============Related to Task Execution Role===================

//This is the executor role
resource "aws_iam_role" "ual_iap_lambda_execution_role" {
  name               = "ual-iap-lambda-execution-${local.environment}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

# Temp policy for testing purposes
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect = "Allow"

    principals {
      type = "AWS"
      identifiers = [
        "arn:aws:iam::367815980639:role/operator"
      ]
    }

    actions = ["sts:AssumeRole"]
  }
}


# This is the real lambda assume policy but for testing purposes for this PR we will use the above assume policy
#data "aws_iam_policy_document" "lambda_assume" {
#  statement {
#    actions = ["sts:AssumeRole"]
#
#    principals {
#      type        = "Service"
#      identifiers = ["lambda.amazonaws.com"]
#    }
#  }
#}

resource "aws_iam_policy" "ual_iap_lambda_execution" {
  name   = "ual-iap-s3-${local.environment}"
  policy = data.aws_iam_policy_document.ual_iap_lambda.json
}

resource "aws_iam_role_policy_attachment" "ual_iap_lambda_attachment" {
  role       = aws_iam_role.ual_iap_lambda_execution_role.id
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

  statement {
    sid       = "AllowS3ActionsInBucket"
    effect    = "Allow"
    resources = ["${module.ual_iap_s3.arn}/*"]
    actions   = ["s3:PutObject", "s3:GetObject"]
  }

  statement {
    sid    = "AllowKms"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:GenerateDataKey",
    ]
    resources = [module.ual_iap_s3.arn]
  }
}
