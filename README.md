# LoanOps Agent — Internal AI Platform

Hybrid (local-first, AWS-deployable) **citation-grounded AI platform** for
enterprise teams — API/capability discovery (EAKG + MCP), docs search, and
grounded answers for any internal role (not care-rep-only).

## Quick start

```powershell
# 1. Copy env and configure local providers
cp .env.example .env

# 2. Install
make install

# 3. Lint + test
make lint test

# 4. Ingest synthetic SOPs
make ingest

# 5. Run demo (agent_api :8000 + web_ui :5173)
make demo
```

Live loan answers use SSE OpenAPI (`packages/sse` via `call_sse_api`). There is
**no** `apps/tools_api` — that mock HTTP service was removed (ADR-010).

The chat agent still calls tools in-process. A separate Model Context Protocol
listener (ADR-011) speaks Streamable HTTP for other clients. It does not replace
`/chat` or the custom `/mcp/tools` JSON routes.

```powershell
# Bearer is required. Empty MCP__AUTH_TOKEN rejects every MCP call.
$env:MCP__AUTH_TOKEN = "<set-a-token>"
python -m packages.mcp_server
# listens on 127.0.0.1:8001/mcp
```

## AI / agent context

Read **`AGENTS.md`** before generating or reviewing code.
Track work in **`TASKS.md`**; append session notes to **`logs.md`**.

This repo has a **Graphify knowledge graph** (`graphify-out/graph.json`) for fast
codebase/architecture questions. Prefer `graphify query "<question>"` over grepping.
Setup and commands: **`GRAPHIFY_SETUP.md`**.

## Layout

```
LoanOps Agent_Demos/
  apps/
    agent_api/      FastAPI /chat, /health, /mcp/tools, streaming, audit log
    web_ui/         React + TypeScript rep UI
  packages/
    agent_core/     Agent + multi-turn SSE tool loop
    mcp_server/     Streamable HTTP MCP listener (not the /mcp/tools JSON API)
    sse/            OpenAPI catalog search + live API invoke
    db/             Optional read-only SQL (dev role)
    docs/           Docs search over vector store
    wiki/           Wiki specialist stubs
    rag/            Ingest, chunk, embed
    safety/         PII redaction + content safety
    eval/           Ragas + custom metrics + CI gate
    common/
      settings.py   Pydantic Settings (single env source)
      schemas.py    Shared Pydantic models
      providers/    Provider Abstraction layer (load-bearing)
  data/
    sops/           ~30 synthetic SOPs
    loans.json      50 synthetic loans
    golden.jsonl    50 Q&A golden items
  infra/
    terraform/      AWS IaC
    scripts/        deployment hooks
  docs/
    01-servicing-agent-prompts.md  Project brief (do not edit)
    03-eval-strategy.md
  ARCHITECTURE.md               Living architecture (single file)
```
## Key constraints

- **Local-first**: `make demo` must work without any AWS credentials.
- **Provider Abstraction**: all external capabilities are Protocols; swap
  local ↔ AWS via env vars only. See `docs/01-servicing-agent-prompts.md` §A.6.1.
- **No PII in code or commits**. All loan data is synthetic.
- **Eval gate is sacred**: never weaken a threshold; fix the root cause instead.
