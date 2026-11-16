terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.env_name
      Project     = var.app_name
      ManagedBy   = "Terraform"
    }
  }
}

# Dev = cost (Spot×1, Aurora pause). Prod = HA for chat path (On-Demand×2+, Aurora min≥0.5).
locals {
  is_prod                 = contains(["prod", "production"], lower(var.env_name))
  service_desired_count   = coalesce(var.service_desired_count, local.is_prod ? 2 : 1)
  use_fargate_spot        = var.use_fargate_spot != null ? var.use_fargate_spot : !local.is_prod
  aurora_min_acu          = coalesce(var.aurora_min_acu, local.is_prod ? 0.5 : 0)
  enable_container_insights = var.enable_container_insights != null ? var.enable_container_insights : local.is_prod
}

module "network" {
  source = "./modules/network"

  app_name                   = var.app_name
  env_name                   = var.env_name
  vpc_cidr                   = var.vpc_cidr
  create_network             = var.create_network
  network_stack_name         = var.network_stack_name
  runtime_subnet_name_prefix = var.runtime_subnet_name_prefix
  db_subnet_name_prefix      = var.db_subnet_name_prefix
}

# Shared ECS SG created before Neptune/Aurora so their ingress can reference it.
resource "aws_security_group" "ecs" {
  name        = "${var.app_name}-${var.env_name}-ecs-sg"
  description = "LoanOps ECS Fargate tasks (Agent API, MCP, sync jobs)"
  vpc_id      = module.network.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

module "neptune" {
  source = "./modules/neptune"

  app_name                  = var.app_name
  env_name                  = var.env_name
  vpc_id                    = module.network.vpc_id
  db_subnet_ids             = module.network.db_subnet_ids
  client_security_group_ids = [aws_security_group.ecs.id]
  min_ncu                   = var.neptune_min_ncu
  max_ncu                   = var.neptune_max_ncu
}

module "rds" {
  source = "./modules/rds"

  app_name                  = var.app_name
  env_name                  = var.env_name
  vpc_id                    = module.network.vpc_id
  db_subnet_ids             = module.network.db_subnet_ids
  client_security_group_ids = [aws_security_group.ecs.id]
  min_acu                   = local.aurora_min_acu
  max_acu                   = var.aurora_max_acu
  auto_pause_seconds        = var.aurora_auto_pause_seconds
}

module "secrets" {
  source = "./modules/secrets"

  app_name      = var.app_name
  env_name      = var.env_name
  postgres_dsn  = module.rds.postgres_dsn
  pgvector_dsn  = module.rds.pgvector_dsn
  auth0_domain  = var.auth0_domain
  langfuse_host = var.langfuse_host
}

module "iam" {
  source = "./modules/iam"

  app_name                = var.app_name
  env_name                = var.env_name
  github_repo             = var.github_repo
  neptune_db_resource_arn = module.neptune.neptune_db_resource_arn
  secret_arns             = [module.secrets.secret_arn]
}

module "ecr" {
  source   = "./modules/ecr"
  app_name = var.app_name
}

module "ecs" {
  source = "./modules/ecs"

  app_name                  = var.app_name
  env_name                  = var.env_name
  aws_region                = var.aws_region
  vpc_id                    = module.network.vpc_id
  alb_subnet_ids            = module.network.alb_subnet_ids
  runtime_subnet_ids        = module.network.runtime_subnet_ids
  extra_security_group_ids  = var.extra_security_group_ids
  ecs_security_group_id     = aws_security_group.ecs.id
  ecs_task_role_arn         = module.iam.ecs_task_role_arn
  ecs_execution_role_arn    = module.iam.ecs_execution_role_arn
  agent_image_url           = module.ecr.agent_image_url
  mcp_image_url             = module.ecr.mcp_image_url
  secret_arn                = module.secrets.secret_arn
  graph_query_url           = module.neptune.sparql_query_url
  graph_update_url          = module.neptune.sparql_update_url
  internal_alb              = true
  cpu_architecture          = var.cpu_architecture
  fargate_cpu               = var.fargate_cpu
  fargate_memory            = var.fargate_memory
  service_desired_count     = local.service_desired_count
  use_fargate_spot          = local.use_fargate_spot
  enable_container_insights = local.enable_container_insights
  acm_certificate_arn       = var.acm_certificate_arn
  route53_zone_id           = var.route53_zone_id
  api_domain_name           = var.api_domain_name
}

module "jobs" {
  source = "./modules/jobs"

  app_name            = var.app_name
  env_name            = var.env_name
  aws_region          = var.aws_region
  cluster_arn         = module.ecs.cluster_arn
  subnet_ids          = module.network.runtime_subnet_ids
  security_group_ids  = module.ecs.task_security_group_ids
  execution_role_arn  = module.iam.ecs_execution_role_arn
  task_role_arn       = module.iam.ecs_task_role_arn
  image_url           = module.ecr.mcp_image_url
  secret_arn          = module.secrets.secret_arn
  graph_query_url     = module.neptune.sparql_query_url
  graph_update_url    = module.neptune.sparql_update_url
  log_group_name      = module.ecs.log_group_name
  nightly_schedule    = var.nightly_schedule
  audit_schedule      = var.audit_schedule
  apiindex_schedule   = var.apiindex_schedule
  sop_ingest_schedule = var.sop_ingest_schedule
  cpu_architecture    = var.cpu_architecture
  use_fargate_spot    = var.jobs_use_fargate_spot
}

module "ui" {
  count  = var.enable_web_ui ? 1 : 0
  source = "./modules/ui"

  app_name = var.app_name
  env_name = var.env_name
}
