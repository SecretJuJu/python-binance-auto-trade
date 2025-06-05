terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Default VPC
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "map-public-ip-on-launch"
    values = ["true"]
  }
}

# ECR Repository
resource "aws_ecr_repository" "bitcoin_trading" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"

  lifecycle_policy {
    policy = jsonencode({
      rules = [
        {
          rulePriority = 1
          description  = "Keep only 10 most recent images"
          selection = {
            tagStatus   = "any"
            countType   = "imageCountMoreThan"
            countNumber = 10
          }
          action = {
            type = "expire"
          }
        }
      ]
    })
  }

  tags = var.common_tags
}

# S3 Bucket for trading state
resource "aws_s3_bucket" "trading_state" {
  bucket = "${var.project_name}-state-${data.aws_caller_identity.current.account_id}-${data.aws_region.current.name}"
  tags   = var.common_tags
}

resource "aws_s3_bucket_versioning" "trading_state" {
  bucket = aws_s3_bucket.trading_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "trading_state" {
  bucket = aws_s3_bucket.trading_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# SNS Topic for notifications
resource "aws_sns_topic" "trading_alerts" {
  name = "${var.project_name}-alerts"
  tags = var.common_tags
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "bitcoin_trading" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 30
  tags              = var.common_tags
}

# ECS Cluster
resource "aws_ecs_cluster" "bitcoin_trading" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = var.common_tags
}

# IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_execution_role" {
  name = "${var.project_name}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Role for ECS Task
resource "aws_iam_role" "ecs_task_role" {
  name = "${var.project_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy" "ecs_task_policy" {
  name = "${var.project_name}-ecs-task-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.trading_state.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.trading_alerts.arn
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.binance_credentials.arn
      }
    ]
  })
}

# Secrets Manager for Binance API credentials
resource "aws_secretsmanager_secret" "binance_credentials" {
  name        = "${var.project_name}/binance"
  description = "Binance API credentials for Bitcoin trading bot"
  tags        = var.common_tags
}

# ECS Task Definition
resource "aws_ecs_task_definition" "bitcoin_trading" {
  family                   = "${var.project_name}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "bitcoin-trading-container"
      image = "${aws_ecr_repository.bitcoin_trading.repository_url}:latest"
      
      essential = true
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.bitcoin_trading.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "ecs"
        }
      }
      
      environment = [
        {
          name  = "SNS_TOPIC_ARN"
          value = aws_sns_topic.trading_alerts.arn
        },
        {
          name  = "S3_BUCKET"
          value = aws_s3_bucket.trading_state.id
        },
        {
          name  = "AWS_DEFAULT_REGION"
          value = data.aws_region.current.name
        },
        {
          name  = "NOTIFY_ON_SUCCESS"
          value = tostring(var.notify_on_success)
        }
      ]
      
      secrets = [
        {
          name      = "BINANCE_API_KEY"
          valueFrom = "${aws_secretsmanager_secret.binance_credentials.arn}:api_key::"
        },
        {
          name      = "BINANCE_SECRET"
          valueFrom = "${aws_secretsmanager_secret.binance_credentials.arn}:secret::"
        }
      ]
    }
  ])

  tags = var.common_tags
}

# IAM Role for EventBridge
resource "aws_iam_role" "eventbridge_role" {
  name = "${var.project_name}-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy" "eventbridge_policy" {
  name = "${var.project_name}-eventbridge-policy"
  role = aws_iam_role.eventbridge_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:RunTask"
        ]
        Resource = aws_ecs_task_definition.bitcoin_trading.arn
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = [
          aws_iam_role.ecs_execution_role.arn,
          aws_iam_role.ecs_task_role.arn
        ]
      }
    ]
  })
}

# EventBridge Rule - 10분마다 실행
resource "aws_cloudwatch_event_rule" "bitcoin_trading_schedule" {
  name                = "${var.project_name}-schedule"
  description         = "Run Bitcoin Trading Bot every 10 minutes"
  schedule_expression = var.schedule_expression
  
  tags = var.common_tags
}

# EventBridge Target - ECS Task
resource "aws_cloudwatch_event_target" "ecs_target" {
  rule      = aws_cloudwatch_event_rule.bitcoin_trading_schedule.name
  target_id = "BitcoinTradingTarget"
  arn       = aws_ecs_cluster.bitcoin_trading.arn
  role_arn  = aws_iam_role.eventbridge_role.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.bitcoin_trading.arn
    launch_type         = "FARGATE"
    platform_version    = "LATEST"

    network_configuration {
      subnets          = data.aws_subnets.default.ids
      assign_public_ip = true
      security_groups  = [aws_security_group.ecs_tasks.id]
    }
  }
} 