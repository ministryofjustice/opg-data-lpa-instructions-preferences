data "aws_ecr_repository" "mock_sirius" {
  provider = aws.management
  name     = "integrations/lpa-iap-mock-sirius"
}

resource "aws_ecs_task_definition" "lpa_iap_mock_sirius" {
  family                   = "lpa-iap-mock-sirius-${terraform.workspace}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  container_definitions    = "[${local.lpa_iap_mock_sirius}]"
  task_role_arn            = aws_iam_role.lpa_iap_mock_sirius.arn
  execution_role_arn       = aws_iam_role.execution_role.arn
}

resource "aws_ecs_service" "mock_sirius" {
  name                    = aws_ecs_task_definition.lpa_iap_mock_sirius.family
  cluster                 = aws_ecs_cluster.lpa_iap.id
  task_definition         = aws_ecs_task_definition.lpa_iap_mock_sirius.arn
  desired_count           = var.use_mock_sirius == "1" ? 1 : 0
  launch_type             = "FARGATE"
  platform_version        = "1.4.0"
  enable_ecs_managed_tags = true
  propagate_tags          = "SERVICE"
  wait_for_steady_state   = true

  network_configuration {
    security_groups  = [aws_security_group.lpa_iap_mock_sirius.id]
    subnets          = var.subnets
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.lpa_iap_mock_sirius.arn
  }
}

locals {
  lpa_iap_mock_sirius = jsonencode({
    cpu       = 0,
    essential = true,
    image     = "${data.aws_ecr_repository.mock_sirius.repository_url}:${var.image_tag}",
    name      = "mock-sirius",
    logConfiguration = {
      logDriver = "awslogs",
      options = {
        awslogs-group         = aws_cloudwatch_log_group.lpa_iap.name,
        awslogs-region        = "eu-west-1",
        awslogs-stream-prefix = "lpa-iap-mock-sirius-${var.environment}"
      }
    },
  })
}

resource "aws_ecs_cluster" "lpa_iap" {
  name = "lpa-iap-${var.environment}"
}

resource "aws_cloudwatch_log_group" "lpa_iap" {
  name              = "lpa-iap-${var.environment}"
  retention_in_days = 3
}

//EXECUTION ROLES

resource "aws_iam_role" "execution_role" {
  name               = "lpa-iap-execution-role.${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.execution_role_assume_policy.json
}

data "aws_iam_policy_document" "execution_role_assume_policy" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      identifiers = ["ecs-tasks.amazonaws.com"]
      type        = "Service"
    }
  }
}

resource "aws_iam_role_policy" "execution_role" {
  policy = data.aws_iam_policy_document.execution_role.json
  role   = aws_iam_role.execution_role.id
}

data "aws_iam_policy_document" "execution_role" {
  statement {
    effect    = "Allow"
    resources = ["*"]

    actions = [
      "ecr:GetAuthorizationToken",
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "ssm:GetParameters",
      "secretsmanager:GetSecretValue",
    ]
  }
}

//TASK ROLE
resource "aws_iam_role" "lpa_iap_mock_sirius" {
  assume_role_policy = data.aws_iam_policy_document.task_role_assume_policy.json
  name               = "lpa-iap-mock-sirius-${var.environment}"
}

data "aws_iam_policy_document" "task_role_assume_policy" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      identifiers = ["ecs-tasks.amazonaws.com"]
      type        = "Service"
    }
  }
}
