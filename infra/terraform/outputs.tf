output "vpc_id" {
  value       = module.vpc.vpc_id
  description = "The ID of the VPC"
}

output "ecs_cluster_name" {
  value       = module.ecs.cluster_name
  description = "Name of the ECS Cluster"
}

output "github_actions_role_arn" {
  value       = module.iam.github_actions_role_arn
  description = "The ARN of the IAM role for GitHub Actions"
}

output "agent_api_url" {
  value       = module.ecs.agent_api_alb_dns
  description = "DNS name of the Agent API Application Load Balancer"
}

output "tools_api_url" {
  value       = module.ecs.tools_api_alb_dns
  description = "DNS name of the Tools API Application Load Balancer"
}
