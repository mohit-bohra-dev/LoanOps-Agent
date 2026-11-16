# LoanOps AWS Architecture + Identity Auth (build spec)

**Diagram:** [`loanops-aws-auth.drawio`](./loanops-aws-auth.drawio). Open in [diagrams.net](https://app.diagrams.net/) (File → Open).  
**Source of truth:** `infra/terraform`. The diagram follows the Terraform modules (`ecs`, `jobs`, `rds`, `neptune`, `ui`, `secrets`, `iam`, `ecr`, `network`).  
**Built with:** [vidanov/aws-architecture-diagram-skill](https://github.com/vidanov/aws-architecture-diagram-skill) and validated with the [awslabs/agent-plugins](https://github.com/awslabs/agent-plugins) `validate_drawio.py` (PASS).  
**Date:** 2026-11-13 | **Version:** v2

The diagram is meant to answer infra questions without a walkthrough. Each arrow carries a teal step number. The Steps and FAQ panels on the canvas repeat the content below.

## Steps

1. A person opens LoanOps (browser) or connects Cursor. OneLogin shows the login page and checks the password against Active Directory.
2. OneLogin hands the identity to Auth0 (SAML). Auth0 issues a signed user JWT.
3. Browser only: the React UI loads from CloudFront, which reads the private S3 bucket via OAC. Cursor skips this step.
4. The client calls the **internal ALB** over HTTPS with `Authorization: Bearer <JWT>`. DNS comes from Route 53, the TLS cert from ACM.
5. The ALB routes by path. `/chat* /eval* /pipelines* /health /mcp/tools*` go to `agent-api` :8000. `/mcp /mcp/* /ready` go to `mcp-server` :8001, which is where Cursor connects.
6. **TARGET (not built):** the service verifies the JWT and asks AppServices AppAuth whether this person and app have a LoanOps role. No role returns 403. Today there is a single shared token, `MCP__AUTH_TOKEN`.
7. The Agent calls MCP tools at `mcp-server.loanops.local:8001` (Cloud Map private DNS). It never goes back through the ALB.
8. The Agent calls Bedrock (LLM + embeddings) and stores sessions and vectors in Aurora.
9. MCP finds the right API using the capability graph in Neptune (SPARQL, IAM SigV4) and the ApiIndex vectors in Aurora.
10. MCP gets a bot token from the Auth0 M2M tenant and caches it until it expires.
11. MCP calls the Plaisse API with a **read-only GET** and the bot token. Plaisse sees the LoanOps bot, not the person.
12. The answer and citations return the same way. Logs go to CloudWatch, traces to Langfuse.
13. EventBridge Scheduler starts the pipeline task in the **same cluster** on this UTC schedule: 02:00 EAKG nightly, 02:30 ApiIndex, 03:00 SOP ingest, Mon 06:00 audit.
14. The pipeline task pulls GitLab repos, OpenAPI specs and Confluence SOP pages.
15. The pipeline writes Aurora (EAKG, ApiIndex, doc vectors) and Neptune (graph), then exits.
16. Deploy: GitHub Actions assumes an IAM role via OIDC (no stored keys), pushes ARM64 images to ECR and updates the ECS services. Tasks read secrets from Secrets Manager when they start.

## Infra decisions

**Are all Fargate tasks in the same cluster?** Yes. Each env has one ECS cluster, `loanops-<env>-cluster`. It runs:

| Workload | Kind | Port | Size | Capacity |
|---|---|---|---|---|
| `agent-api` | ECS service (always on) | 8000 | 0.25 vCPU / 0.5 GB | dev 1× Spot · prod 2× On-Demand |
| `mcp-server` | ECS service (always on) | 8001 | 0.25 vCPU / 0.5 GB | dev 1× Spot · prod 2× On-Demand |
| `eakg-sync` | Scheduled task (4 crons) | — | 0.5 vCPU / 1 GB | Spot in every env |

All three run ARM64 Graviton in the runtime subnets. They share one ECS security group, one task IAM role and one log group. Each has its own task definition, so each deploys and scales on its own.

**Why two services?** `agent-api` is the chat brain (LLM and sessions). `mcp-server` is the shared tool server used by the Agent, Cursor and other MCP clients.

**Dev vs Prod** (same Terraform; `env_name` switches the defaults):

| Setting | dev | prod |
|---|---|---|
| Agent / MCP tasks | 1 each, Spot | 2 each, On-Demand, across runtime subnets (2 AZs) |
| Pipeline task | Spot | Spot |
| Aurora min ACU | 0 (pauses after 5 min) | 0.5 |
| Neptune | 1→2 NCU | 1→2 NCU |
| Container Insights | off | on |
| ALB TLS | HTTP :80 if no cert | HTTPS :443 via `acm_certificate_arn` |

**Network:** the corp VPC is discovered (`create_network=false`), not created. The ALB is internal (corp or VPN only), and tasks have no public IP.

**Security groups:**
- ALB SG accepts 80/443.
- ECS SG accepts 8000–8001 from the ALB SG, and 8001 from itself (Agent to MCP).
- Aurora (5432) and Neptune (8182) accept traffic only from the ECS SG.

**Secrets:** one secret, `loanops-<env>-app`, injected when a task starts.

**Built vs target:**
- Built: every AWS box on the diagram, M2M calls to Plaisse, and the shared MCP token.
- Target: step 6 (per-person JWT plus AppAuth).
- Optional later: on-behalf-of, so Plaisse sees the person.

**Out of scope:** EC2, NAT or public ingress, and write calls to Plaisse (GET only).

## Lucid

The team ARC canvas is still [LoanOps AWS Architecture](https://lucid.app/lucidchart/729e9984-d335-4bdc-bb6e-9a1a238a4208/edit). The auth version is on the page **ARC + Identity Auth (Auth0 / OneLogin)**, and the original ARC page is untouched.
