# LoanOps AWS Serverless Architecture (ARC Reference)

100% managed / serverless AWS stack — zero EC2 nodes to patch, scale-to-zero where AWS supports it, Graviton `ARM64` + `FARGATE_SPOT` for compute.

## Architecture & Serverless Stack

| Layer | AWS Service | Serverless / Cost posture | Est. Dev / Mo |
|---|---|---|---|
| **Web UI** | **S3 (private) + CloudFront OAC** | Pure serverless ($0 idle, pay per request) | **~$0–$1** |
| **Ingress / DNS** | **Route 53 + Internal ALB** (HTTPS w/ ACM) | Managed L7 routing: `/chat*` → `:8000`, `/mcp*` → `:8001` | **~$16** |
| **Service Mesh** | **AWS Cloud Map** (`mcp-server.<app>.local`) | Private DNS for Agent API → MCP hop (pennies/resource) | **~$0.20** |
| **Runtime Compute** | **ECS Fargate + Graviton ARM64** | Dev: Spot ×1 each (Agent+MCP). Prod HA: On-Demand ×2+ multi-AZ, ALB `/health` | **~$5–$7** (dev) |
| **Batch Pipelines** | **EventBridge Scheduler → Fargate Spot** | `$0` idle; Spot even in prod (best-effort, not HA): `eakg-nightly`, `apiindex-nightly`, `sop-ingest-nightly`, `eakg-audit` | **~$1** |
| **Relational + Vectors** | **Aurora PostgreSQL 16 Serverless v2 (`pgvector`)** | Dev: `min=0` ACU auto-pause. Prod: `min≥0.5` ACU (no pause) | **~$2–$15** |
| **Enterprise KG (SPARQL)** | **Neptune Serverless** (`:8182/sparql`, SigV4) | Serverless NCU scaling (`1.0–2.0 NCU`; AWS minimum floor is `1.0 NCU`) | **~$85** *(floor)* |
| **LLM + Embeddings** | **Amazon Bedrock** (Nova Pro + Titan Embed v2 1024d) | Pure token-based serverless | **Pay-per-token** |
| **Secrets & Logs** | **Secrets Manager + CloudWatch (14d) + ECR (keep 10)** | Container Insights off in dev; ECR lifecycle auto-expires old images | **~$2–$4** |

> **Why Fargate (not Lambda) for Agent API / MCP?**  
> Both `/chat` (SSE) and `:8001/mcp` (MCP Streamable HTTP + warm ApiIndex memory) are long-lived/streaming ASGI apps. Identical Docker images locally and in AWS; no 15-minute Lambda limit.
>
> **HA posture (env-aware defaults):**  
> `env_name=prod` → Agent+MCP On-Demand, `desired_count=2`, Aurora `min_acu=0.5`, Container Insights on.  
> `env_name=dev` → Spot ×1, Aurora `min_acu=0` (pause), Insights off.  
> Pipelines always Spot (`jobs_use_fargate_spot=true`) — not on the chat critical path. Override with `service_desired_count` / `use_fargate_spot` / `aurora_min_acu`.
>
> **Biggest cost lever to discuss at ARC:**  
> Everything except Neptune idles near `$0`–`$25/mo` in corp VPC (`create_network=false`, no NAT Gateway). Neptune Serverless has an AWS-enforced `1.0 NCU` minimum (~$85/mo); pause/stop cluster outside demo hours in dev if strict budget applies.

## Apply

### Corp VPC (`plaisse` pattern — recommended, no NAT cost)

```hcl
create_network           = false
extra_security_group_ids = ["sg-..."]          # corp allow-list SG
acm_certificate_arn      = "arn:aws:acm:..."   # enables HTTPS :443 + HTTP 301 redirect
route53_zone_id          = "Z..."              # optional internal DNS
api_domain_name          = "loanops.dev.internal"
```

### Sandbox VPC

```powershell
cd infra/terraform
terraform init
terraform validate
terraform plan
```

## Post-apply checklist

1. Build & push `linux/arm64` images to ECR `*-agent-api` and `*-mcp-server`.
2. Populate Auth0 M2M + Langfuse keys in Secrets Manager `${app_name}-${env_name}-app`.
3. Enable vector extension once on Aurora: `CREATE EXTENSION IF NOT EXISTS vector;`
4. Sync built React UI (`apps/web_ui/dist`) to `web_ui_bucket`.
