# Discover corp VPC (plaisse pattern) or create a sandbox VPC.

variable "app_name" { type = string }
variable "env_name" { type = string }
variable "vpc_cidr" { type = string }
variable "create_network" { type = bool }
variable "network_stack_name" { type = string }
variable "runtime_subnet_name_prefix" { type = string }
variable "db_subnet_name_prefix" { type = string }

locals {
  network_stack_name = var.network_stack_name != "" ? var.network_stack_name : "infra-network-${var.env_name}"
}

# --- Create path (sandbox) ---
data "aws_availability_zones" "available" {
  count = var.create_network ? 1 : 0
  state = "available"
}

module "vpc" {
  count   = var.create_network ? 1 : 0
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.app_name}-${var.env_name}-vpc"
  cidr = var.vpc_cidr

  azs             = slice(data.aws_availability_zones.available[0].names, 0, 2)
  private_subnets = [cidrsubnet(var.vpc_cidr, 8, 1), cidrsubnet(var.vpc_cidr, 8, 2)]
  public_subnets  = [cidrsubnet(var.vpc_cidr, 8, 101), cidrsubnet(var.vpc_cidr, 8, 102)]

  enable_nat_gateway = true
  single_nat_gateway = true
}

# --- Discover path (corp) ---
data "aws_vpc" "corp" {
  count = var.create_network ? 0 : 1
  tags = {
    "aws:cloudformation:stack-name" = local.network_stack_name
  }
}

data "aws_subnets" "runtime" {
  count = var.create_network ? 0 : 1
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.corp[0].id]
  }
  filter {
    name   = "tag:Name"
    values = ["${var.runtime_subnet_name_prefix} *"]
  }
}

data "aws_subnets" "db" {
  count = var.create_network ? 0 : 1
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.corp[0].id]
  }
  filter {
    name   = "tag:Name"
    values = ["${var.db_subnet_name_prefix} *"]
  }
}

data "aws_subnets" "public" {
  count = var.create_network ? 0 : 1
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.corp[0].id]
  }
  filter {
    name   = "tag:Name"
    values = ["Public *"]
  }
}

locals {
  vpc_id = var.create_network ? module.vpc[0].vpc_id : data.aws_vpc.corp[0].id
  # Internal ALB still needs two subnets; prefer public when present, else runtime.
  alb_subnet_ids = var.create_network ? module.vpc[0].public_subnets : (
    length(data.aws_subnets.public[0].ids) >= 2 ? sort(data.aws_subnets.public[0].ids) : sort(data.aws_subnets.runtime[0].ids)
  )
  runtime_subnet_ids = var.create_network ? module.vpc[0].private_subnets : sort(data.aws_subnets.runtime[0].ids)
  db_subnet_ids      = var.create_network ? module.vpc[0].private_subnets : sort(data.aws_subnets.db[0].ids)
}

output "vpc_id" {
  value = local.vpc_id
}

output "alb_subnet_ids" {
  value = local.alb_subnet_ids
}

output "runtime_subnet_ids" {
  value = local.runtime_subnet_ids
}

output "db_subnet_ids" {
  value = local.db_subnet_ids
}
