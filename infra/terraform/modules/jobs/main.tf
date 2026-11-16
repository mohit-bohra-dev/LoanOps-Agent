# Serverless scheduled pipelines (EventBridge Scheduler -> Fargate Spot ARM64 tasks).
# $0 idle cost; runs EAKG nightly, weekly audit, ApiIndex vectors, and SOP/docs ingest.

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
variable "apiindex_schedule" { type = string }
variable "sop_ingest_schedule" { type = string }
variable "cpu_architecture" {
  type    = string
  default = "ARM64"
}
variable "use_fargate_spot" {
  type    = bool
  default = true
}

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
    { name = "VECTOR_STORE__PGVECTOR_DIMENSIONS", value = "1024" },
    { name = "EAKG_STORE__BACKEND", value = "postgres" },
    { name = "EAKG__ENVIRONMENT", value = var.env_name },
    { name = "GRAPH_STORE__QUERY_URL", value = var.graph_query_url },
    { name = "GRAPH_STORE__UPDATE_URL", value = var.graph_update_url },
    { name = "GRAPH_STORE__AUTH_MODE", value = "sigv4" },
    { name = "GRAPH_STORE__REGION", value = var.aws_region },
    { name = "EMBEDDING__PROVIDER", value = "bedrock" },
    { name = "EMBEDDING__BEDROCK__REGION", value = var.aws_region },
    { name = "LLM__PROVIDER", value = "bedrock" },
    { name = "LLM__BEDROCK__REGION", value = var.aws_region },
    { name = "AWS_REGION", value = var.aws_region },
  ]
  secrets = [
    for k in [
      "VECTOR_STORE__PGVECTOR_DSN",
      "EAKG_STORE__DSN",
      "MCP__AUTH_TOKEN",
      "CREDENTIALS__AUTH0_DOMAIN",
      "CREDENTIALS__AUTH0_CLIENT_ID",
      "CREDENTIALS__AUTH0_CLIENT_SECRET",
    ] : {
      name      = k
      valueFrom = "${var.secret_arn}:${k}::"
    }
  ]

  schedules = {
    "eakg-nightly" = {
      expression = var.nightly_schedule
      command    = ["python", "-m", "packages.eakg", "sync", "nightly"]
    }
    "eakg-audit" = {
      expression = var.audit_schedule
      command    = ["python", "-m", "packages.eakg", "sync", "audit"]
    }
    "apiindex-nightly" = {
      expression = var.apiindex_schedule
      command    = ["python", "-m", "packages.pipelines", "start", "openapi_to_api_index", "--env", var.env_name, "--triggered-by", "schedule:apiindex"]
    }
    "sop-ingest-nightly" = {
      expression = var.sop_ingest_schedule
      command    = ["python", "-m", "packages.pipelines", "start", "sop_to_doc_embeddings", "--env", var.env_name, "--triggered-by", "schedule:sop_ingest"]
    }
  }
}

resource "aws_ecs_task_definition" "sync" {
  family                   = "${var.app_name}-${var.env_name}-eakg-sync"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = var.cpu_architecture
  }

  container_definitions = jsonencode([{
    name        = "eakg-sync"
    image       = "${var.image_url}:latest"
    essential   = true
    environment = local.env
    secrets     = local.secrets
    command     = ["python", "-m", "packages.eakg", "sync", "nightly"]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.log_group_name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "pipelines"
      }
    }
  }])
}

resource "aws_scheduler_schedule" "pipelines" {
  for_each   = local.schedules
  name       = "${var.app_name}-${var.env_name}-${each.key}"
  group_name = "default"
  flexible_time_window { mode = "OFF" }
  schedule_expression = each.value.expression

  target {
    arn      = var.cluster_arn
    role_arn = aws_iam_role.scheduler.arn
    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.sync.arn
      capacity_provider_strategy {
        capacity_provider = var.use_fargate_spot ? "FARGATE_SPOT" : "FARGATE"
        weight            = 1
        base              = 0
      }
      network_configuration {
        subnets          = var.subnet_ids
        security_groups  = var.security_group_ids
        assign_public_ip = false
      }
    }
    input = jsonencode({
      containerOverrides = [{
        name    = "eakg-sync"
        command = each.value.command
      }]
    })
  }
}

output "sync_task_definition_arn" {
  value = aws_ecs_task_definition.sync.arn
}

output "schedule_names" {
  value = [for s in aws_scheduler_schedule.pipelines : s.name]
}
