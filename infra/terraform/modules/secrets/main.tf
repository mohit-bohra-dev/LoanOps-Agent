# App secrets created here for sandbox. Corp accounts often create via pipeline by name.
# Holds DSNs + MCP bearer + outbound Auth0 M2M + Langfuse telemetry keys.

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
variable "auth0_domain" {
  type    = string
  default = "auth.dev.pennymac.plaisse.com"
}
variable "auth0_client_id" {
  type    = string
  default = ""
}
variable "auth0_client_secret" {
  type      = string
  default   = ""
  sensitive = true
}
variable "langfuse_host" {
  type    = string
  default = ""
}
variable "langfuse_public_key" {
  type    = string
  default = ""
}
variable "langfuse_secret_key" {
  type      = string
  default   = ""
  sensitive = true
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
  name                    = "${var.app_name}-${var.env_name}-app"
  description             = "LoanOps Agent runtime secrets (Aurora DSNs, MCP token, Auth0 M2M, Langfuse)"
  recovery_window_in_days = var.env_name == "prod" ? 7 : 0
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    SESSION_STORE__POSTGRES_DSN        = var.postgres_dsn
    VECTOR_STORE__PGVECTOR_DSN         = var.pgvector_dsn
    EAKG_STORE__DSN                    = var.postgres_dsn
    MCP__AUTH_TOKEN                    = local.mcp_token
    TOOLS_CLIENT__PROVIDER             = "mcp"
    CREDENTIALS__AUTH0_DOMAIN          = var.auth0_domain
    CREDENTIALS__AUTH0_CLIENT_ID       = var.auth0_client_id
    CREDENTIALS__AUTH0_CLIENT_SECRET   = var.auth0_client_secret
    TELEMETRY__LANGFUSE__HOST          = var.langfuse_host
    TELEMETRY__LANGFUSE__PUBLIC_KEY    = var.langfuse_public_key
    TELEMETRY__LANGFUSE__SECRET_KEY    = var.langfuse_secret_key
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
