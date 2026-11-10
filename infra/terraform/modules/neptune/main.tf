# Neptune Serverless — product SPARQL store (ADR-026). Replaces GraphDB + EFS.

variable "app_name" { type = string }
variable "env_name" { type = string }
variable "vpc_id" { type = string }
variable "db_subnet_ids" { type = list(string) }
variable "client_security_group_ids" { type = list(string) }
variable "min_ncu" { type = number }
variable "max_ncu" { type = number }

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

resource "aws_security_group" "neptune" {
  name        = "${var.app_name}-${var.env_name}-neptune-sg"
  description = "Neptune SPARQL :8182 from ECS tasks"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 8182
    to_port         = 8182
    protocol        = "tcp"
    security_groups = var.client_security_group_ids
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_neptune_subnet_group" "this" {
  name       = "${var.app_name}-${var.env_name}-neptune"
  subnet_ids = var.db_subnet_ids
}

resource "aws_neptune_cluster" "this" {
  cluster_identifier                   = "${var.app_name}-${var.env_name}"
  engine                               = "neptune"
  neptune_subnet_group_name            = aws_neptune_subnet_group.this.name
  vpc_security_group_ids               = [aws_security_group.neptune.id]
  storage_encrypted                    = true
  iam_database_authentication_enabled  = true
  skip_final_snapshot                  = true
  apply_immediately                    = true
  enable_cloudwatch_logs_exports       = ["audit"]

  serverless_v2_scaling_configuration {
    min_capacity = var.min_ncu
    max_capacity = var.max_ncu
  }
}

resource "aws_neptune_cluster_instance" "this" {
  cluster_identifier = aws_neptune_cluster.this.id
  instance_class     = "db.serverless"
  engine             = "neptune"
  apply_immediately  = true
}

output "endpoint" {
  value = aws_neptune_cluster.this.endpoint
}

output "sparql_query_url" {
  value = "https://${aws_neptune_cluster.this.endpoint}:8182/sparql"
}

output "sparql_update_url" {
  value = "https://${aws_neptune_cluster.this.endpoint}:8182/sparql"
}

output "security_group_id" {
  value = aws_security_group.neptune.id
}

output "cluster_arn" {
  value = aws_neptune_cluster.this.arn
}

# Data-plane IAM uses neptune-db ARN + cluster_resource_id, not the rds:cluster ARN.
output "neptune_db_resource_arn" {
  value = "arn:aws:neptune-db:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:cluster:${aws_neptune_cluster.this.cluster_resource_id}"
}
