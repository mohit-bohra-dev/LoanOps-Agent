output "vpc_id" {
  value       = module.network.vpc_id
  description = "VPC id (created or discovered)"
}

output "ecs_cluster_name" {
  value       = module.ecs.cluster_name
  description = "ECS cluster name"
}

output "alb_dns" {
  value       = module.ecs.alb_dns
  description = "Internal ALB DNS (Agent API + MCP path rules)"
}

output "agent_api_url" {
  value       = "http://${module.ecs.alb_dns}"
  description = "Base URL for /chat (HTTP; add ACM for HTTPS)"
}

output "neptune_sparql_query_url" {
  value       = module.neptune.sparql_query_url
  description = "Set as GRAPH_STORE__QUERY_URL (AUTH_MODE=sigv4)"
}

output "neptune_sparql_update_url" {
  value       = module.neptune.sparql_update_url
  description = "Set as GRAPH_STORE__UPDATE_URL"
}

output "rds_endpoint" {
  value       = module.rds.endpoint
  description = "Postgres hostname"
}

output "ecr_agent_repository" {
  value = module.ecr.agent_image_url
}

output "ecr_mcp_repository" {
  value = module.ecr.mcp_image_url
}

output "github_actions_role_arn" {
  value       = module.iam.github_actions_role_arn
  description = "OIDC role for GitHub Actions push/deploy"
}

output "app_secret_arn" {
  value       = module.secrets.secret_arn
  description = "Secrets Manager JSON with DSNs + MCP__AUTH_TOKEN"
}

output "sync_task_definition_arn" {
  value       = module.jobs.sync_task_definition_arn
  description = "EAKG nightly/audit Fargate task definition"
}
