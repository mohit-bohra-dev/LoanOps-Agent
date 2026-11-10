# App secrets created here for sandbox. Corp accounts often create via pipeline by name.

variable "app_name" { type = string }
variable "env_name" { type = string }
variable "postgres_dsn" {
  type      = string
  sensitive = true
}
variable "pgvector_dsn" {
  type      = string
  sensitive = true
}
variable "mcp_auth_token" {
  type    = string
  default = ""
}

resource "random_password" "mcp_token" {
  count   = var.mcp_auth_token == "" ? 1 : 0
  length  = 48
  special = false
}

locals {
  mcp_token = var.mcp_auth_token != "" ? var.mcp_auth_token : random_password.mcp_token[0].result
}

resource "aws_secretsmanager_secret" "app" {
  name        = "${var.app_name}-${var.env_name}-app"
  description = "LoanOps Agent runtime secrets"
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    SESSION_STORE__POSTGRES_DSN   = var.postgres_dsn
    VECTOR_STORE__PGVECTOR_DSN    = var.pgvector_dsn
    EAKG_STORE__DSN               = var.postgres_dsn
    MCP__AUTH_TOKEN               = local.mcp_token
    TOOLS_CLIENT__PROVIDER        = "mcp"
  })
}

output "secret_arn" {
  value = aws_secretsmanager_secret.app.arn
}

output "secret_name" {
  value = aws_secretsmanager_secret.app.name
}

output "mcp_auth_token" {
  value     = local.mcp_token
  sensitive = true
}
