variable "app_name" {}
variable "env_name" {}
variable "ecs_task_role_name" {}

resource "aws_secretsmanager_secret" "app_secrets" {
  name        = "${var.app_name}-${var.env_name}-secrets"
  description = "Application secrets for LoanOps Agent"
}

# Initial placeholder secret value
resource "aws_secretsmanager_secret_version" "app_secrets_initial" {
  secret_id     = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    "GEMINI_API_KEY" = "placeholder",
    "QDRANT_API_KEY" = "placeholder",
    "TOOLS_API_TOKEN" = "placeholder"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# Allow ECS Task Role to read the secret
resource "aws_iam_policy" "secrets_access" {
  name        = "${var.app_name}-${var.env_name}-secrets-access"
  description = "Allow reading secrets from Secrets Manager"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.app_secrets.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "secrets_access_attach" {
  role       = var.ecs_task_role_name
  policy_arn = aws_iam_policy.secrets_access.arn
}

output "secret_arn" {
  value = aws_secretsmanager_secret.app_secrets.arn
}
