# Scheduled EAKG sync (nightly + weekly audit). Same image as MCP/agent tooling.

variable "app_name" { type = string }
variable "env_name" { type = string }
variable "aws_region" { type = string }
variable "cluster_arn" { type = string }
variable "subnet_ids" { type = list(string) }
variable "security_group_ids" { type = list(string) }
variable "execution_role_arn" { type = string }
variable "task_role_arn" { type = string }
variable "image_url" { type = string }
variable "secret_arn" { type = string }
variable "graph_query_url" { type = string }
variable "graph_update_url" { type = string }
variable "log_group_name" { type = string }
variable "nightly_schedule" { type = string }
variable "audit_schedule" { type = string }

resource "aws_iam_role" "scheduler" {
  name = "${var.app_name}-${var.env_name}-scheduler-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "scheduler" {
  name = "${var.app_name}-${var.env_name}-scheduler"
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecs:RunTask"]
        Resource = [aws_ecs_task_definition.sync.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [var.execution_role_arn, var.task_role_arn]
      }
    ]
  })
}

locals {
  env = [
    { name = "TOOLS_CLIENT__PROVIDER", value = "mcp" },
    { name = "VECTOR_STORE__PROVIDER", value = "pgvector" },
    { name = "EAKG_STORE__BACKEND", value = "postgres" },
    { name = "GRAPH_STORE__QUERY_URL", value = var.graph_query_url },
    { name = "GRAPH_STORE__UPDATE_URL", value = var.graph_update_url },
    { name = "GRAPH_STORE__AUTH_MODE", value = "sigv4" },
    { name = "GRAPH_STORE__REGION", value = var.aws_region },
    { name = "AWS_REGION", value = var.aws_region },
  ]
  secrets = [
    for k in ["VECTOR_STORE__PGVECTOR_DSN", "EAKG_STORE__DSN", "MCP__AUTH_TOKEN"] : {
      name      = k
      valueFrom = "${var.secret_arn}:${k}::"
    }
  ]
}

resource "aws_ecs_task_definition" "sync" {
  family                   = "${var.app_name}-${var.env_name}-eakg-sync"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([{
    name        = "eakg-sync"
    image       = "${var.image_url}:latest"
    essential   = true
    environment = local.env
    secrets     = local.secrets
    # Command overridden per schedule via containerOverrides
    command = ["python", "-m", "packages.eakg", "sync", "nightly"]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.log_group_name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "eakg-sync"
      }
    }
  }])
}

resource "aws_scheduler_schedule" "nightly" {
  name       = "${var.app_name}-${var.env_name}-eakg-nightly"
  group_name = "default"
  flexible_time_window { mode = "OFF" }
  schedule_expression = var.nightly_schedule

  target {
    arn      = var.cluster_arn
    role_arn = aws_iam_role.scheduler.arn
    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.sync.arn
      launch_type         = "FARGATE"
      network_configuration {
        subnets          = var.subnet_ids
        security_groups  = var.security_group_ids
        assign_public_ip = false
      }
    }
    input = jsonencode({
      containerOverrides = [{
        name    = "eakg-sync"
        command = ["python", "-m", "packages.eakg", "sync", "nightly"]
      }]
    })
  }
}

resource "aws_scheduler_schedule" "audit" {
  name       = "${var.app_name}-${var.env_name}-eakg-audit"
  group_name = "default"
  flexible_time_window { mode = "OFF" }
  schedule_expression = var.audit_schedule

  target {
    arn      = var.cluster_arn
    role_arn = aws_iam_role.scheduler.arn
    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.sync.arn
      launch_type         = "FARGATE"
      network_configuration {
        subnets          = var.subnet_ids
        security_groups  = var.security_group_ids
        assign_public_ip = false
      }
    }
    input = jsonencode({
      containerOverrides = [{
        name    = "eakg-sync"
        command = ["python", "-m", "packages.eakg", "sync", "audit"]
      }]
    })
  }
}

output "sync_task_definition_arn" {
  value = aws_ecs_task_definition.sync.arn
}
