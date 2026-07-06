variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "env_name" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "servicing-agent"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "agent_image_url" {
  description = "ECR image URL for the Agent API"
  type        = string
  default     = "504132672333.dkr.ecr.us-east-1.amazonaws.com/servicing-agent-api:latest"
}

variable "tools_image_url" {
  description = "ECR image URL for the Tools API"
  type        = string
  default     = "504132672333.dkr.ecr.us-east-1.amazonaws.com/servicing-tools-api:latest"
}
