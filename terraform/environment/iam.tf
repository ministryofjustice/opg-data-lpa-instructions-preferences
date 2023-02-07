//===============Related to Task Execution Role===================

//This is the role that gets assumed from ECS task with assume_role attached
resource "aws_iam_role" "ual_iap_lambda_execution_role" {
  name               = "ual-iap-lambda-execution-${local.environment}"
  assume_role_policy = data.aws_iam_policy_document.ual_iap_lambda.json
}

// Access policy for the s3 bucket
data "aws_iam_policy_document" "ual_iap_lambda" {
  statement {
    sid       = "AllowS3ActionsInBucket"
    effect    = "Allow"
    resources = ["${module.ual_iap_s3.arn}/*", "${module.ual_iap_s3.arn}"]
    actions   = ["s3:*"]
  }
}
