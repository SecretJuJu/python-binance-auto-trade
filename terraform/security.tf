# Security Group for ECS Tasks
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks"
  description = "Security group for ECS tasks"
  vpc_id      = data.aws_vpc.default.id

  # Outbound rules - Allow all outbound traffic for API calls
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-ecs-tasks"
  })

  lifecycle {
    ignore_changes        = [tags]
    prevent_destroy       = true
    create_before_destroy = false
  }
} 