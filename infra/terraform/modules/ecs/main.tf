# Agent API (:8000) + MCP server (:8001) on serverless ECS Fargate (ARM64 Graviton + Fargate Spot).
# TOOLS_CLIENT__PROVIDER=mcp. Agent -> MCP over AWS Cloud Map; Corp users/IDEs -> Internal ALB (HTTPS when ACM set).

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
variable "cpu_architecture" {
  type    = string
  default = "ARM64"
}
variable "fargate_cpu" {
  type    = number
  default = 256
}
variable "fargate_memory" {
  type    = number
  default = 512
}
variable "service_desired_count" {
  type    = number
  default = 1
}
variable "use_fargate_spot" {
  type    = bool
  default = true
}
variable "enable_container_insights" {
  type    = bool
  default = false
}
variable "log_retention_days" {
  type    = number
  default = 14
}
variable "acm_certificate_arn" {
  type    = string
  default = ""
}
variable "route53_zone_id" {
  type    = string
  default = ""
}
variable "api_domain_name" {
  type    = string
  default = ""
}
variable "credentials_provider" {
  type    = string
  default = "auth0_m2m"
}
variable "telemetry_provider" {
  type    = string
  default = "langfuse"
}

locals {
  use_https = var.acm_certificate_arn != ""
}

resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-${var.env_name}-cluster"
  setting {
    name  = "containerInsights"
    value = var.enable_container_insights ? "enabled" : "disabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name       = aws_ecs_cluster.main.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = var.use_fargate_spot ? "FARGATE_SPOT" : "FARGATE"
    weight            = 1
    base              = 0
  }
}

resource "aws_security_group" "alb" {
  name        = "${var.app_name}-${var.env_name}-alb-sg"
  vpc_id      = var.vpc_id
  description = "Internal ALB for Agent API + MCP"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
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

# Allow Agent API tasks to call MCP tasks on :8001 via Cloud Map DNS.
resource "aws_security_group_rule" "ecs_self_mcp" {
  type              = "ingress"
  from_port         = 8001
  to_port           = 8001
  protocol          = "tcp"
  security_group_id = var.ecs_security_group_id
  self              = true
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.app_name}-${var.env_name}"
  retention_in_days = var.log_retention_days
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

  dynamic "default_action" {
    for_each = local.use_https ? [1] : []
    content {
      type = "redirect"
      redirect {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }

  dynamic "default_action" {
    for_each = local.use_https ? [] : [1]
    content {
      type = "fixed-response"
      fixed_response {
        content_type = "text/plain"
        message_body = "Not Found"
        status_code  = "404"
      }
    }
  }
}

resource "aws_lb_listener" "https" {
  count             = local.use_https ? 1 : 0
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Not Found"
      status_code  = "404"
    }
  }
}

resource "aws_route53_record" "alb" {
  count   = var.route53_zone_id != "" && var.api_domain_name != "" ? 1 : 0
  zone_id = var.route53_zone_id
  name    = var.api_domain_name
  type    = "A"

  alias {
    name                   = aws_lb.api.dns_name
    zone_id                = aws_lb.api.zone_id
    evaluate_target_health = true
  }
}

locals {
  active_listener_arn = local.use_https ? aws_lb_listener.https[0].arn : aws_lb_listener.http.arn

  common_env = [
    { name = "TOOLS_CLIENT__PROVIDER", value = "mcp" },
    { name = "VECTOR_STORE__PROVIDER", value = "pgvector" },
    { name = "VECTOR_STORE__PGVECTOR_DIMENSIONS", value = "1024" },
    { name = "SESSION_STORE__PROVIDER", value = "postgres" },
    { name = "EAKG_STORE__BACKEND", value = "postgres" },
    { name = "API_INDEX__ENABLED", value = "true" },
    { name = "GRAPH_STORE__QUERY_URL", value = var.graph_query_url },
    { name = "GRAPH_STORE__UPDATE_URL", value = var.graph_update_url },
    { name = "GRAPH_STORE__AUTH_MODE", value = "sigv4" },
    { name = "GRAPH_STORE__REGION", value = var.aws_region },
    { name = "LLM__PROVIDER", value = "bedrock" },
    { name = "LLM__BEDROCK__REGION", value = var.aws_region },
    { name = "EMBEDDING__PROVIDER", value = "bedrock" },
    { name = "EMBEDDING__BEDROCK__REGION", value = var.aws_region },
    { name = "CREDENTIALS__PROVIDER", value = var.credentials_provider },
    { name = "TELEMETRY__PROVIDER", value = var.telemetry_provider },
    { name = "TELEMETRY__LANGFUSE__ENVIRONMENT", value = var.env_name },
    { name = "AWS_REGION", value = var.aws_region },
  ]
  secret_keys = [
    "SESSION_STORE__POSTGRES_DSN",
    "VECTOR_STORE__PGVECTOR_DSN",
    "EAKG_STORE__DSN",
    "MCP__AUTH_TOKEN",
    "CREDENTIALS__AUTH0_DOMAIN",
    "CREDENTIALS__AUTH0_CLIENT_ID",
    "CREDENTIALS__AUTH0_CLIENT_SECRET",
    "TELEMETRY__LANGFUSE__HOST",
    "TELEMETRY__LANGFUSE__PUBLIC_KEY",
    "TELEMETRY__LANGFUSE__SECRET_KEY",
  ]
  common_secrets = [
    for k in local.secret_keys : {
      name      = k
      valueFrom = "${var.secret_arn}:${k}::"
    }
  ]
  task_sgs = concat([var.ecs_security_group_id], var.extra_security_group_ids)
}

# --- Agent API (:8000) ---
resource "aws_ecs_task_definition" "agent" {
  family                   = "${var.app_name}-${var.env_name}-agent-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.fargate_cpu
  memory                   = var.fargate_memory
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = var.cpu_architecture
  }

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
  listener_arn = local.active_listener_arn
  priority     = 100
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.agent.arn
  }
  condition {
    path_pattern { values = ["/chat*", "/health", "/version", "/eval*", "/pipelines*", "/mcp/tools*"] }
  }
}

resource "aws_ecs_service" "agent" {
  name            = "agent-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.agent.arn
  desired_count   = var.service_desired_count

  capacity_provider_strategy {
    capacity_provider = var.use_fargate_spot ? "FARGATE_SPOT" : "FARGATE"
    weight            = 1
    base              = var.use_fargate_spot ? 0 : 1
  }

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

# --- MCP server (:8001) + Cloud Map private DNS ---
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
  cpu                      = var.fargate_cpu
  memory                   = var.fargate_memory
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = var.cpu_architecture
  }

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
  listener_arn = local.active_listener_arn
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
  desired_count   = var.service_desired_count

  capacity_provider_strategy {
    capacity_provider = var.use_fargate_spot ? "FARGATE_SPOT" : "FARGATE"
    weight            = 1
    base              = var.use_fargate_spot ? 0 : 1
  }

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
output "base_url" {
  value = var.api_domain_name != "" ? "${local.use_https ? "https" : "http"}://${var.api_domain_name}" : "${local.use_https ? "https" : "http"}://${aws_lb.api.dns_name}"
}
output "mcp_internal_dns" { value = "mcp-server.${var.app_name}.local:8001" }
output "ecs_security_group_id" { value = var.ecs_security_group_id }
output "execution_role_arn" { value = var.ecs_execution_role_arn }
output "task_role_arn" { value = var.ecs_task_role_arn }
output "runtime_subnet_ids" { value = var.runtime_subnet_ids }
output "task_security_group_ids" { value = local.task_sgs }
output "log_group_name" { value = aws_cloudwatch_log_group.api.name }
