variable "app_name" {}

resource "aws_ecr_repository" "agent_api" {
  name                 = "${var.app_name}-agent-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "tools_api" {
  name                 = "${var.app_name}-tools-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

output "agent_image_url" {
  value = aws_ecr_repository.agent_api.repository_url
}

output "tools_image_url" {
  value = aws_ecr_repository.tools_api.repository_url
}
