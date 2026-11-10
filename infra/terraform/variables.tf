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

variable "db_instance_class" {
  description = "RDS Postgres instance class"
  type        = string
  default     = "db.t4g.medium"
}

variable "neptune_min_ncu" {
  description = "Neptune Serverless min capacity (NCU)"
  type        = number
  default     = 1.0
}

variable "neptune_max_ncu" {
  description = "Neptune Serverless max capacity (NCU)"
  type        = number
  default     = 8.0
}

variable "github_repo" {
  description = "GitHub repo for OIDC deploy role"
  type        = string
  default     = "mohit-bohra-dev/LoanOps-Agent"
}

variable "nightly_schedule" {
  description = "EventBridge cron for EAKG nightly sync (UTC)"
  type        = string
  default     = "cron(0 2 * * ? *)"
}

variable "audit_schedule" {
  description = "EventBridge cron for EAKG weekly audit (UTC Monday 06:00)"
  type        = string
  default     = "cron(0 6 ? * MON *)"
}
