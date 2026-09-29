# Servicing Agent — AI Agent Instructions

> Read this file before generating any code. Re-read §Tech Stack and §Rules
> whenever you are about to make a design choice.

## What this project is

An **internal copilot for licensed mortgage-servicing care reps** at a US
mortgage servicer. Hybrid architecture: identical Python codebase runs
locally (Ollama + Qdrant) or on AWS (Bedrock + Qdrant Cloud) via env-var swap.
Full brief: `docs/01-servicing-agent-prompts.md`.

## Read order

| File | Purpose |
|------|---------|
| `AGENTS.md` (this file) | Architecture & constraints |
| `CONTEXT.md` | Quick-reference companion (env vars, ports, scaffold status, one-liners) |
| `TASKS.md` | Active work — check before starting |
| `decisions.md` | Settled ADRs |
| `docs/01-servicing-agent-prompts.md` | Full project brief (source of truth) |
| `packages/common/settings.py` | Every env var, single source |
| `packages/common/providers/` | Provider abstraction layer |

## Knowledge graph (Graphify) — mandatory

This project has a **Graphify knowledge graph** at `graphify-out/graph.json`.
You **MUST** consult it before grepping, reading raw files, or guessing at
architecture. This applies to every agentic IDE (Cursor, Gemini, Copilot,
Windsurf, etc.).

### When to use it

| Situation | Command |
|-----------|---------|
| Codebase / architecture question | `graphify query "<question>"` |
| How two components connect | `graphify path "<A>" "<B>"` |
| Explain a concept or module | `graphify explain "<concept>"` |
| Broad architecture overview | Read `graphify-out/GRAPH_REPORT.md` (only if query/path/explain insufficient) |
| Wiki navigation | If `graphify-out/wiki/index.md` exists, navigate it instead of raw files |

### Rules

1. **Graph-first research**: Before any `grep`, `find`, or exploratory file
   read, run `graphify query` or `graphify path`. These return a scoped
   subgraph that is smaller and more relevant than raw grep output.
2. **Keep the graph current**: After modifying code files, run
   `graphify update .` to refresh the graph (AST-only, no API cost).
3. **Never skip this step**: If `graphify-out/graph.json` exists, you are
   expected to use it. Failure to consult the graph when it would have
   answered the question is a workflow violation.

## Tech stack

| Layer | Local (dev) | AWS (target) |
|-------|-------------|----------------|
| Language | Python 3.11 | Python 3.11 |
| API framework | FastAPI | FastAPI on ECS Fargate |
| Orchestration | Microsoft Agent Framework | Same + Prompt Flow |
| LLM | Ollama Llama 3.1 8B | Amazon Bedrock GPT-4o |
| Embeddings | bge-small-en-v1.5 | text-embedding-3-large |
| Vector store | Qdrant (Docker) | Qdrant Cloud |
| PII | Presidio | Presidio |
| Content safety | Rule-based stub | AWS Content Safety |
| Audit log | JSONL on disk | CloudWatch Logs + S3 |
| Observability | OTel to console | CloudWatch Logs |
| Secrets | .env | AWS Secrets Manager |
| UI | React + TypeScript (Vite) | Static Web Apps |

## Provider Abstraction (load-bearing rule)

Every external capability is a **Provider**: a `typing.Protocol` + one or
more concrete implementations + a factory function. No application code may
import a concrete provider class directly.

- Protocols live in `packages/common/providers/<name>.py`
- Factories: `get_chat_provider()`, `get_vector_store_provider()`, etc.
  in `packages/common/providers/factory.py`
- Selection is by env var via `packages/common/settings.py` only
- 10 provider categories: chat, embedding, vector_store, pii,
  content_safety, audit_sink, secrets, telemetry, tools_client, prompt_store

## Rules (non-negotiable)

- **Graphify-first**: When `graphify-out/graph.json` exists, always run `graphify query` / `graphify path` before grepping or reading raw source files. See §Knowledge graph above.
- **Local-first**: `make demo` must work with zero AWS credentials.
- **No concrete imports** outside `packages/common/providers/` — CI grep gate enforces this.
- **No `os.environ` / `os.getenv`** outside `packages/common/settings.py`.
- **No PII** anywhere in code, test fixtures, or commits. Use synthetic data.
- **No mutating tool calls** in v1 (no payments, no plan starts, no holds).
- **Eval gate is sacred**: never change a threshold downward. Fix the cause.
- **Every factual answer must have a citation** (`policy:` or `tool:` prefix).
- **uv** for all Python env management. Never raw `pip install`.
- **Async Python** throughout the backend.
- **mypy --strict** on all packages. No `Any` without an explicit `# type: ignore` comment explaining why.
- **Windows PowerShell shell**: this workspace runs `powershell` (v5.1). Never use bash-only syntax. In particular, **`&&` and `||` are invalid** (`'&&' is not a valid statement separator`). Chain with `;`, use separate calls, or `if ($?) { ... }`. See `.cursor/rules/shell-powershell.mdc`.

## Quick reference

> Where things go — use this table to find the right file.

| What | Where |
|------|-------|
| Agent system prompt | `docs/01-servicing-agent-prompts.md` §B |
| Env vars / config | `packages/common/settings.py` |
| Provider Protocols | `packages/common/providers/<name>.py` |
| Provider factories | `packages/common/providers/factory.py` |
| InMemory providers (tests) | `packages/common/providers/testing.py` |
| Contract tests | `packages/common/providers/contract_tests/` |
| Shared Pydantic models | `packages/common/schemas.py` |
| Live SSE OpenAPI tools | `packages/sse/` + `/mcp/tools` |
| Agent API (`/chat`, `/health`) | `apps/agent_api/` |
| RAG ingest CLI | `packages/rag/ingest.py` |
| Safety middleware | `packages/safety/` |
| Eval runner + metrics | `packages/eval/` |
| Golden Q&A set | `data/golden.jsonl` |
| Synthetic SOPs | `data/sops/` |
| Synthetic loans | `data/loans.json` |
| AWS IaC | `infra/terraform/` |

## Module layout

```
apps/
  agent_api/    FastAPI :8000  /chat (SSE), /health, /mcp/tools
  web_ui/       React + TypeScript rep UI (Vite)

packages/
  agent_core/   Microsoft Agent Framework agent, prompt loader, intent router
  rag/          Chunker, ingest CLI, retrieval
  safety/       PII + content-safety middleware
  eval/         Ragas + custom metrics, golden runner, CI gate
  common/       Settings, schemas, Provider layer
```

## Approval required before

These changes require explicit human approval before proceeding:

- New ADR / architecture change
- New environment variables
- Schema-breaking migrations
- Changing any eval threshold
- Adding a new external capability (must add a Provider Protocol first)

## Common workflows

### Build a step

Execute a single numbered build step from the project brief.

1. Read `AGENTS.md`
2. Run `graphify query "<step description>"` to understand affected modules
3. Read `TASKS.md` — confirm step is not already done
4. Read `docs/01-servicing-agent-prompts.md` §C for the step's acceptance criteria
5. Implement the step
6. Run `graphify update .` to refresh the graph
7. Mark tasks done in `TASKS.md`
8. Append entry to `logs.md`
9. Confirm acceptance criteria pass before returning

### Check provider invariants

Verify the Provider Abstraction invariants hold across the codebase:

1. `grep -R "from packages.common.providers.*import.*Provider" apps/ packages/agent_core packages/rag packages/safety packages/eval` — must return zero matches for concrete classes.
2. `grep -RnE "os\.environ|os\.getenv" --include="*.py" .` excluding `settings.py` and `tests/` — must be empty.
3. Run `pytest packages/common/providers/contract_tests` — all green.
4. Run `mypy --strict packages/common` — no errors.

## After each session

1. Mark completed items in `TASKS.md` (`- [ ]` → `- [x]`)
2. Append a dated entry to `logs.md`
3. Update `decisions.md` for any new ADR
4. Update `docs/02-architecture.md` or `docs/03-eval-strategy.md` if relevant
