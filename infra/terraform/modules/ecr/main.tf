variable "app_name" { type = string }

resource "aws_ecr_repository" "agent_api" {
  name                 = "${var.app_name}-agent-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "mcp_server" {
  name                 = "${var.app_name}-mcp-server"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

output "agent_image_url" {
  value = aws_ecr_repository.agent_api.repository_url
}

output "mcp_image_url" {
  value = aws_ecr_repository.mcp_server.repository_url
}
