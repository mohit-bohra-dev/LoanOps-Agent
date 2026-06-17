# Servicing Agent for Internal Care Reps

Hybrid (local-first, Azure-deployable) copilot for licensed mortgage-servicing
care representatives at a US mortgage servicer.

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

# 5. Run full demo (tools_api + agent_api + web_ui)
make demo
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
    agent_api/      FastAPI /chat, /health, streaming, audit log
    tools_api/      FastAPI 5 mock servicing endpoints
    web_ui/         React + TypeScript rep UI
  packages/
    agent_core/     Microsoft Agent Framework agent + router
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
    bicep/          Azure IaC
    scripts/        azd hooks
  docs/
    01-servicing-agent-prompts.md  Project brief (do not edit)
    02-architecture.md
    03-eval-strategy.md
```

## Key constraints

- **Local-first**: `make demo` must work without any Azure credentials.
- **Provider Abstraction**: all external capabilities are Protocols; swap
  local Ã¢â€ â€ Azure via env vars only. See `docs/01-servicing-agent-prompts.md` Ã‚Â§A.6.1.
- **No PII in code or commits**. All loan data is synthetic.
- **Eval gate is sacred**: never weaken a threshold; fix the root cause instead.
