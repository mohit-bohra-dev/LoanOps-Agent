variable "app_name" { type = string }

locals {
  lifecycle_policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 3 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 3
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep last 10 tagged images"
        selection = {
          tagStatus     = "any"
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = { type = "expire" }
      }
    ]
  })
}

resource "aws_ecr_repository" "agent_api" {
  name                 = "${var.app_name}-agent-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "agent_api" {
  repository = aws_ecr_repository.agent_api.name
  policy     = local.lifecycle_policy
}

resource "aws_ecr_repository" "mcp_server" {
  name                 = "${var.app_name}-mcp-server"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "mcp_server" {
  repository = aws_ecr_repository.mcp_server.name
  policy     = local.lifecycle_policy
}

output "agent_image_url" {
  value = aws_ecr_repository.agent_api.repository_url
}

output "mcp_image_url" {
  value = aws_ecr_repository.mcp_server.repository_url
}
