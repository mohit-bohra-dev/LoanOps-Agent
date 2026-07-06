terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region

  default_tags {
    tags = {
      Environment = var.env_name
      Project     = var.app_name
      ManagedBy   = "Terraform"
    }
  }
}

module "vpc" {
  source = "./modules/vpc"

  app_name = var.app_name
  env_name = var.env_name
  vpc_cidr = var.vpc_cidr
}

module "iam" {
  source   = "./modules/iam"
  app_name = var.app_name
  env_name = var.env_name
}

module "ecr" {
  source   = "./modules/ecr"
  app_name = var.app_name
}

module "secrets" {
  source = "./modules/secrets"

  app_name = var.app_name
  env_name = var.env_name
  ecs_task_role_name = module.iam.ecs_task_role_name
}

module "ecs" {
  source = "./modules/ecs"

  app_name             = var.app_name
  env_name             = var.env_name
  vpc_id               = module.vpc.vpc_id
  public_subnets         = module.vpc.public_subnets
  private_subnets        = module.vpc.private_subnets
  ecs_task_role_arn      = module.iam.ecs_task_role_arn
  ecs_execution_role_arn = module.iam.ecs_execution_role_arn
  agent_image_url        = module.ecr.agent_image_url
  tools_image_url        = module.ecr.tools_image_url
}
