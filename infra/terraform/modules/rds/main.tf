# Aurora PostgreSQL 16 Serverless v2 (pgvector): sessions, EAKG artifacts, ApiIndex, doc/cap vectors.
# min_capacity = 0 enables auto-pause ($0 compute when idle in dev); set 0.5+ in prod for zero wake latency.
# shortcut: run `CREATE EXTENSION IF NOT EXISTS vector;` after first connect (or via RDS Data API / init job).

variable "app_name" { type = string }
variable "env_name" { type = string }
variable "vpc_id" { type = string }
variable "db_subnet_ids" { type = list(string) }
variable "client_security_group_ids" { type = list(string) }
variable "min_acu" {
  type    = number
  default = 0
}
variable "max_acu" {
  type    = number
  default = 2.0
}
variable "auto_pause_seconds" {
  type    = number
  default = 300
}

resource "aws_security_group" "rds" {
  name        = "${var.app_name}-${var.env_name}-aurora-pg-sg"
  description = "Aurora Serverless v2 Postgres from ECS tasks"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
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

resource "aws_db_subnet_group" "this" {
  name       = "${var.app_name}-${var.env_name}-aurora-pg"
  subnet_ids = var.db_subnet_ids
}

resource "random_password" "master" {
  length  = 32
  special = false
}

resource "aws_rds_cluster" "this" {
  cluster_identifier      = "${var.app_name}-${var.env_name}-pg"
  engine                  = "aurora-postgresql"
  engine_mode             = "provisioned"
  engine_version          = "16.6"
  database_name           = "loanops"
  master_username         = "loanops"
  master_password         = random_password.master.result
  db_subnet_group_name    = aws_db_subnet_group.this.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  storage_encrypted       = true
  enable_http_endpoint    = true
  backup_retention_period = var.env_name == "prod" ? 7 : 1
  skip_final_snapshot     = var.env_name != "prod"
  deletion_protection     = var.env_name == "prod"

  serverlessv2_scaling_configuration {
    min_capacity             = var.min_acu
    max_capacity             = var.max_acu
    seconds_until_auto_pause = var.min_acu == 0 ? var.auto_pause_seconds : null
  }
}

resource "aws_rds_cluster_instance" "serverless" {
  identifier         = "${var.app_name}-${var.env_name}-pg-1"
  cluster_identifier = aws_rds_cluster.this.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.this.engine
  engine_version     = aws_rds_cluster.this.engine_version
  publicly_accessible = false
}

output "endpoint" {
  value = aws_rds_cluster.this.endpoint
}

output "port" {
  value = aws_rds_cluster.this.port
}

output "db_name" {
  value = aws_rds_cluster.this.database_name
}

output "username" {
  value = aws_rds_cluster.this.master_username
}

output "password" {
  value     = random_password.master.result
  sensitive = true
}

output "security_group_id" {
  value = aws_security_group.rds.id
}

# DSN shapes used by packages/common/settings.py
output "postgres_dsn" {
  value     = "postgresql://${aws_rds_cluster.this.master_username}:${random_password.master.result}@${aws_rds_cluster.this.endpoint}:${aws_rds_cluster.this.port}/${aws_rds_cluster.this.database_name}"
  sensitive = true
}

output "pgvector_dsn" {
  value     = "postgresql+asyncpg://${aws_rds_cluster.this.master_username}:${random_password.master.result}@${aws_rds_cluster.this.endpoint}:${aws_rds_cluster.this.port}/${aws_rds_cluster.this.database_name}"
  sensitive = true
}
