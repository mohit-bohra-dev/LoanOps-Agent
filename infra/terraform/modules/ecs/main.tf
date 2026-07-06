variable "app_name" {}
variable "env_name" {}
variable "vpc_id" {}
variable "public_subnets" {}
variable "private_subnets" {}
variable "ecs_task_role_arn" {}
variable "ecs_execution_role_arn" {}
variable "agent_image_url" {}
variable "tools_image_url" {}

resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-${var.env_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# --- Application Load Balancers ---
resource "aws_security_group" "alb_sg" {
  name        = "${var.app_name}-${var.env_name}-alb-sg"
  vpc_id      = var.vpc_id
  description = "Security group for the ALB"

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

resource "aws_lb" "api_alb" {
  name               = "${var.app_name}-${var.env_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = var.public_subnets
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.api_alb.arn
  port              = "80"
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

# --- ECS Services Security Group ---
resource "aws_security_group" "ecs_sg" {
  name        = "${var.app_name}-${var.env_name}-ecs-sg"
  vpc_id      = var.vpc_id
  description = "Security group for ECS tasks"

  ingress {
    from_port       = 8000
    to_port         = 8001
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- CloudWatch Logs ---
resource "aws_cloudwatch_log_group" "api_logs" {
  name              = "/ecs/${var.app_name}-${var.env_name}-api"
  retention_in_days = 30
}

# --- Agent API ---
resource "aws_ecs_task_definition" "agent_api" {
  family                   = "${var.app_name}-${var.env_name}-agent-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([{
    name      = "agent-api"
    image     = var.agent_image_url
    essential = true
    portMappings = [{
      containerPort = 8000
      hostPort      = 8000
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api_logs.name
        "awslogs-region"        = "us-east-1"
        "awslogs-stream-prefix" = "agent"
      }
    }
  }])
}

resource "aws_lb_target_group" "agent_api_tg" {
  name        = "${var.app_name}-${var.env_name}-agent-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path = "/health"
  }
}

resource "aws_lb_listener_rule" "agent_api_rule" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.agent_api_tg.arn
  }

  condition {
    path_pattern {
      values = ["/chat*", "/health"]
    }
  }
}

resource "aws_ecs_service" "agent_api" {
  name            = "agent-api-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.agent_api.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnets
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.agent_api_tg.arn
    container_name   = "agent-api"
    container_port   = 8000
  }

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# --- Tools API ---
resource "aws_ecs_task_definition" "tools_api" {
  family                   = "${var.app_name}-${var.env_name}-tools-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([{
    name      = "tools-api"
    image     = var.tools_image_url
    essential = true
    portMappings = [{
      containerPort = 8001
      hostPort      = 8001
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api_logs.name
        "awslogs-region"        = "us-east-1"
        "awslogs-stream-prefix" = "tools"
      }
    }
  }])
}

resource "aws_lb_target_group" "tools_api_tg" {
  name        = "${var.app_name}-${var.env_name}-tools-tg"
  port        = 8001
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path = "/tools"
  }
}

resource "aws_lb_listener_rule" "tools_api_rule" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.tools_api_tg.arn
  }

  condition {
    path_pattern {
      values = ["/tools*", "/lookup_loan*", "/search_borrower*"]
    }
  }
}

resource "aws_ecs_service" "tools_api" {
  name            = "tools-api-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.tools_api.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnets
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.tools_api_tg.arn
    container_name   = "tools-api"
    container_port   = 8001
  }

  lifecycle {
    ignore_changes = [task_definition]
  }
}

output "cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "agent_api_alb_dns" {
  value = aws_lb.api_alb.dns_name
}

output "tools_api_alb_dns" {
  value = aws_lb.api_alb.dns_name
}
