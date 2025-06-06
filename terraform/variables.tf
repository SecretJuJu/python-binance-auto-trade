variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-2"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "bitcoin-auto-trader"
}

variable "ecr_repository_name" {
  description = "ECR repository name"
  type        = string
  default     = "bitcoin-auto-trader"
}

variable "task_cpu" {
  description = "CPU units for the ECS task (1 vCPU = 1024)"
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Memory (in MiB) for the ECS task"
  type        = number
  default     = 1024
}

variable "schedule_expression" {
  description = "EventBridge schedule expression (rate or cron)"
  type        = string
  default     = "rate(10 minutes)"
}

variable "notify_on_success" {
  description = "Whether to send notifications on successful execution"
  type        = bool
  default     = false
}

variable "use_s3_instead_of_dynamodb" {
  description = "Whether to use S3 instead of DynamoDB for state storage"
  type        = bool
  default     = true
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "BitcoinAutoTrader"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

variable "binance_api_key" {
  description = "Binance API Key (set via environment variable or terraform.tfvars)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "binance_secret" {
  description = "Binance Secret Key (set via environment variable or terraform.tfvars)"
  type        = string
  sensitive   = true
  default     = ""
} 