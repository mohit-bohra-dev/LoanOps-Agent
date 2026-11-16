variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "env_name" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "app_name" {
  description = "Application name (resource prefix)"
  type        = string
  default     = "loanops"
}

variable "vpc_cidr" {
  description = "CIDR when create_network=true"
  type        = string
  default     = "10.0.0.0/16"
}

variable "create_network" {
  description = "true = create VPC (sandbox). false = discover corp infra-network-<env> VPC like plaisse."
  type        = bool
  default     = true
}

variable "network_stack_name" {
  description = "CloudFormation stack name for corp VPC when create_network=false. Empty = infra-network-<env_name>."
  type        = string
  default     = ""
}

variable "runtime_subnet_name_prefix" {
  description = "Name-tag prefix for runtime subnets when create_network=false"
  type        = string
  default     = "Lambda"
}

variable "db_subnet_name_prefix" {
  description = "Name-tag prefix for DB subnets when create_network=false"
  type        = string
  default     = "Application"
}

variable "extra_security_group_ids" {
  description = "Extra SGs for ECS tasks (corp allow-list) when create_network=false"
  type        = list(string)
  default     = []
}

# --- Serverless Aurora PostgreSQL v2 (pgvector) ---
variable "aurora_min_acu" {
  description = "Aurora Serverless v2 min ACU. null = env default (dev 0 auto-pause; prod 0.5 no pause)."
  type        = number
  default     = null
}

variable "aurora_max_acu" {
  description = "Aurora Serverless v2 max ACU"
  type        = number
  default     = 2.0
}

variable "aurora_auto_pause_seconds" {
  description = "Idle seconds before Aurora Serverless v2 pauses when aurora_min_acu = 0"
  type        = number
  default     = 300
}

# --- Serverless Neptune ---
variable "neptune_min_ncu" {
  description = "Neptune Serverless min capacity (NCU; AWS floor is 1.0)"
  type        = number
  default     = 1.0
}

variable "neptune_max_ncu" {
  description = "Neptune Serverless max capacity (NCU)"
  type        = number
  default     = 2.0
}

# --- Serverless Fargate (ARM64 Graviton + Spot) ---
variable "cpu_architecture" {
  description = "ECS Fargate CPU architecture (ARM64 Graviton = ~20% cheaper than X86_64)"
  type        = string
  default     = "ARM64"
}

variable "fargate_cpu" {
  description = "Fargate vCPU units per service task (256 = 0.25 vCPU)"
  type        = number
  default     = 256
}

variable "fargate_memory" {
  description = "Fargate memory MiB per service task"
  type        = number
  default     = 512
}

variable "service_desired_count" {
  description = "Desired task count for Agent API and MCP. null = env default (dev 1; prod 2 for HA)."
  type        = number
  default     = null
}

variable "use_fargate_spot" {
  description = "FARGATE_SPOT for Agent/MCP services. null = env default (dev true; prod false On-Demand HA)."
  type        = bool
  default     = null
}

variable "jobs_use_fargate_spot" {
  description = "FARGATE_SPOT for EventBridge batch pipelines (always best-effort; default true even in prod)"
  type        = bool
  default     = true
}

variable "enable_container_insights" {
  description = "ECS Container Insights. null = env default (dev false; prod true)."
  type        = bool
  default     = null
}

# --- Entry / TLS / Static UI ---
variable "enable_web_ui" {
  description = "Provision serverless S3 + CloudFront OAC static Web UI"
  type        = bool
  default     = true
}

variable "acm_certificate_arn" {
  description = "Optional ACM cert ARN for HTTPS :443 on Internal ALB (empty = HTTP :80 sandbox)"
  type        = string
  default     = ""
}

variable "route53_zone_id" {
  description = "Optional Route 53 hosted zone ID for Internal ALB alias"
  type        = string
  default     = ""
}

variable "api_domain_name" {
  description = "Optional DNS name for Internal ALB (requires route53_zone_id)"
  type        = string
  default     = ""
}

# --- External SaaS / CI ---
variable "github_repo" {
  description = "GitHub repo for OIDC deploy role"
  type        = string
  default     = "mohit-bohra-dev/LoanOps-Agent"
}

variable "auth0_domain" {
  description = "Auth0 M2M domain for Plaisse SSE outbound calls"
  type        = string
  default     = "auth.dev.pennymac.plaisse.com"
}

variable "langfuse_host" {
  description = "Langfuse host URL for MCP/agent telemetry"
  type        = string
  default     = ""
}

# --- EventBridge Schedules (UTC) ---
variable "nightly_schedule" {
  description = "EventBridge cron for EAKG nightly sync (UTC)"
  type        = string
  default     = "cron(0 2 * * ? *)"
}

variable "apiindex_schedule" {
  description = "EventBridge cron for ApiIndex pipeline start (UTC; after EAKG nightly)"
  type        = string
  default     = "cron(30 2 * * ? *)"
}

variable "sop_ingest_schedule" {
  description = "EventBridge cron for Confluence SOP -> docs vectors refresh (UTC)"
  type        = string
  default     = "cron(0 3 * * ? *)"
}

variable "audit_schedule" {
  description = "EventBridge cron for EAKG weekly audit (UTC Monday 06:00)"
  type        = string
  default     = "cron(0 6 ? * MON *)"
}
