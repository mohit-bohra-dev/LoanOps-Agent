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
  description = "Internal ALB DNS (/chat* -> Agent API :8000, /mcp* -> MCP :8001)"
}

output "agent_api_url" {
  value       = module.ecs.base_url
  description = "Base URL for Agent API + remote MCP (HTTPS when acm_certificate_arn set)"
}

output "mcp_internal_dns" {
  value       = module.ecs.mcp_internal_dns
  description = "AWS Cloud Map private DNS used by Agent API -> MCP"
}

output "web_ui_url" {
  value       = var.enable_web_ui ? module.ui[0].ui_url : null
  description = "CloudFront URL for static React Web UI"
}

output "web_ui_bucket" {
  value       = var.enable_web_ui ? module.ui[0].bucket_name : null
  description = "Private S3 bucket for static Web UI assets"
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
  description = "Aurora PostgreSQL Serverless v2 cluster endpoint"
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
  description = "Secrets Manager JSON with Aurora DSNs, MCP__AUTH_TOKEN, Auth0 M2M, Langfuse"
}

output "sync_task_definition_arn" {
  value       = module.jobs.sync_task_definition_arn
  description = "Serverless Fargate Spot batch task definition"
}

output "pipeline_schedules" {
  value       = module.jobs.schedule_names
  description = "EventBridge Scheduler cron names"
}
