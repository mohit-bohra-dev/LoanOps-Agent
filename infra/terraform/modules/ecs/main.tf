# Agent API (:8000) + MCP server (:8001) on Fargate. TOOLS_CLIENT__PROVIDER=mcp.

variable "app_name" { type = string }
variable "env_name" { type = string }
variable "aws_region" { type = string }
variable "vpc_id" { type = string }
variable "alb_subnet_ids" { type = list(string) }
variable "runtime_subnet_ids" { type = list(string) }
variable "extra_security_group_ids" { type = list(string) }
variable "ecs_task_role_arn" { type = string }
variable "ecs_execution_role_arn" { type = string }
variable "agent_image_url" { type = string }
variable "mcp_image_url" { type = string }
variable "secret_arn" { type = string }
variable "graph_query_url" { type = string }
variable "graph_update_url" { type = string }
variable "internal_alb" {
  type    = bool
  default = true
}
variable "ecs_security_group_id" { type = string }

resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-${var.env_name}-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_security_group" "alb" {
  name        = "${var.app_name}-${var.env_name}-alb-sg"
  vpc_id      = var.vpc_id
  description = "ALB for Agent API + MCP"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group_rule" "ecs_from_alb" {
  type                     = "ingress"
  from_port                = 8000
  to_port                  = 8001
  protocol                 = "tcp"
  security_group_id        = var.ecs_security_group_id
  source_security_group_id = aws_security_group.alb.id
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.app_name}-${var.env_name}"
  retention_in_days = 30
}

resource "aws_lb" "api" {
  name               = "${var.app_name}-${var.env_name}-alb"
  internal           = var.internal_alb
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.alb_subnet_ids
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Not Found"
      status_code  = "404"
    }
  }
}

locals {
  common_env = [
    { name = "TOOLS_CLIENT__PROVIDER", value = "mcp" },
    { name = "VECTOR_STORE__PROVIDER", value = "pgvector" },
    { name = "SESSION_STORE__PROVIDER", value = "postgres" },
    { name = "EAKG_STORE__BACKEND", value = "postgres" },
    { name = "GRAPH_STORE__QUERY_URL", value = var.graph_query_url },
    { name = "GRAPH_STORE__UPDATE_URL", value = var.graph_update_url },
    { name = "GRAPH_STORE__AUTH_MODE", value = "sigv4" },
    { name = "GRAPH_STORE__REGION", value = var.aws_region },
    { name = "LLM__PROVIDER", value = "bedrock" },
    { name = "EMBEDDING__PROVIDER", value = "bedrock" },
    { name = "AWS_REGION", value = var.aws_region },
  ]
  secret_keys = [
    "SESSION_STORE__POSTGRES_DSN",
    "VECTOR_STORE__PGVECTOR_DSN",
    "EAKG_STORE__DSN",
    "MCP__AUTH_TOKEN",
  ]
  common_secrets = [
    for k in local.secret_keys : {
      name      = k
      valueFrom = "${var.secret_arn}:${k}::"
    }
  ]
  task_sgs = concat([var.ecs_security_group_id], var.extra_security_group_ids)
}

# --- Agent API ---
resource "aws_ecs_task_definition" "agent" {
  family                   = "${var.app_name}-${var.env_name}-agent-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([{
    name      = "agent-api"
    image     = "${var.agent_image_url}:latest"
    essential = true
    portMappings = [{ containerPort = 8000, hostPort = 8000, protocol = "tcp" }]
    environment = concat(local.common_env, [
      { name = "MCP__HOST", value = "mcp-server.${var.app_name}.local" },
      { name = "MCP__PORT", value = "8001" },
      { name = "MCP__PATH", value = "/mcp" },
    ])
    secrets = local.common_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "agent"
      }
    }
  }])
}

resource "aws_lb_target_group" "agent" {
  name        = "${var.app_name}-${var.env_name}-agent"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  health_check { path = "/health" }
}

resource "aws_lb_listener_rule" "agent" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.agent.arn
  }
  condition {
    path_pattern { values = ["/chat*", "/health", "/version", "/eval*", "/mcp/tools*"] }
  }
}

resource "aws_ecs_service" "agent" {
  name            = "agent-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.agent.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.runtime_subnet_ids
    security_groups  = local.task_sgs
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.agent.arn
    container_name   = "agent-api"
    container_port   = 8000
  }

  lifecycle { ignore_changes = [task_definition] }
}

# --- MCP server ---
resource "aws_service_discovery_private_dns_namespace" "this" {
  name = "${var.app_name}.local"
  vpc  = var.vpc_id
}

resource "aws_service_discovery_service" "mcp" {
  name = "mcp-server"
  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.this.id
    dns_records {
      ttl  = 10
      type = "A"
    }
    routing_policy = "MULTIVALUE"
  }
  health_check_custom_config { failure_threshold = 1 }
}

resource "aws_ecs_task_definition" "mcp" {
  family                   = "${var.app_name}-${var.env_name}-mcp-server"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([{
    name      = "mcp-server"
    image     = "${var.mcp_image_url}:latest"
    essential = true
    portMappings = [{ containerPort = 8001, hostPort = 8001, protocol = "tcp" }]
    environment = concat(local.common_env, [
      { name = "MCP__HOST", value = "0.0.0.0" },
      { name = "MCP__PORT", value = "8001" },
      { name = "MCP__PATH", value = "/mcp" },
      { name = "MCP__ROLE", value = "system" },
    ])
    secrets = local.common_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "mcp"
      }
    }
  }])
}

resource "aws_lb_target_group" "mcp" {
  name        = "${var.app_name}-${var.env_name}-mcp"
  port        = 8001
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  health_check { path = "/health" }
}

resource "aws_lb_listener_rule" "mcp" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 200
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.mcp.arn
  }
  condition {
    path_pattern { values = ["/mcp", "/mcp/*", "/ready"] }
  }
}

resource "aws_ecs_service" "mcp" {
  name            = "mcp-server"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.mcp.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.runtime_subnet_ids
    security_groups  = local.task_sgs
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.mcp.arn
    container_name   = "mcp-server"
    container_port   = 8001
  }

  service_registries {
    registry_arn = aws_service_discovery_service.mcp.arn
  }

  lifecycle { ignore_changes = [task_definition] }
}

output "cluster_name" { value = aws_ecs_cluster.main.name }
output "cluster_arn" { value = aws_ecs_cluster.main.arn }
output "alb_dns" { value = aws_lb.api.dns_name }
output "ecs_security_group_id" { value = var.ecs_security_group_id }
output "execution_role_arn" { value = var.ecs_execution_role_arn }
output "task_role_arn" { value = var.ecs_task_role_arn }
output "runtime_subnet_ids" { value = var.runtime_subnet_ids }
output "task_security_group_ids" { value = local.task_sgs }
output "log_group_name" { value = aws_cloudwatch_log_group.api.name }
