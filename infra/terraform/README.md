# LoanOps AWS Terraform

Fargate Agent API + MCP, RDS Postgres (pgvector), **Neptune Serverless** (SPARQL), EventBridge sync jobs.

## Stack

| Piece | Resource |
|---|---|
| Network | `create_network=true` sandbox VPC, or discover corp `infra-network-<env>` |
| Compute | ECS Fargate: `agent-api` :8000, `mcp-server` :8001 |
| Entry | Internal ALB HTTP (add ACM for HTTPS) |
| Graph | Neptune Serverless SPARQL `:8182/sparql` — `GRAPH_STORE__AUTH_MODE=sigv4` |
| Data | RDS Postgres 16 — sessions, ApiIndex, vectors |
| Jobs | EventBridge → Fargate `eakg sync nightly` / `audit` |
| Secrets | Secrets Manager JSON (`TOOLS_CLIENT__PROVIDER=mcp`) |

## Apply (sandbox)

```powershell
cd infra/terraform
terraform init
terraform plan
terraform apply
```

Corp VPC:

```hcl
create_network             = false
extra_security_group_ids   = ["sg-..."]  # from SSM / platform
```

## After apply

1. Push images to ECR `*-agent-api` and `*-mcp-server`.
2. On RDS: `CREATE EXTENSION IF NOT EXISTS vector;`
3. Agent reaches MCP via Cloud Map: `mcp-server.<app>.local:8001`.

## Out of scope here

S3/CloudFront UI, ACM HTTPS listener, GitLab OnePipeline secrets-by-name-only (sandbox creates the secret).
