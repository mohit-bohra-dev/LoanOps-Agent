#Requires -Version 5.1
<#
.SYNOPSIS
  Initialize the Servicing Agent monorepo skeleton.

.DESCRIPTION
  Scaffolds the exact folder structure, stub source files, AI-tool dot-folders,
  and context markdown files required by the Servicing Agent for Internal Care
  Reps project brief (docs/01-servicing-agent-prompts.md).
  Safe to re-run: skips existing files unless -Force.

.EXAMPLE
  .\docs\Init-Project.ps1 -TargetPath .
  .\docs\Init-Project.ps1 -TargetPath . -Force   # overwrite all
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Position = 0)]
    [string]$TargetPath = (Get-Location).Path,

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

#region Helpers

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        if ($PSCmdlet.ShouldProcess($Path, 'Create directory')) {
            New-Item -ItemType Directory -Path $Path -Force | Out-Null
        }
    }
}

function Write-InitFile {
    param(
        [string]$Root,
        [string]$RelativePath,
        [string]$Content
    )
    $fullPath = Join-Path $Root $RelativePath
    $dir = Split-Path $fullPath -Parent
    if ($dir) { Ensure-Directory -Path $dir }

    if ((Test-Path -LiteralPath $fullPath) -and -not $Force) {
        Write-Verbose "Skip (exists): $RelativePath"
        return 'skipped'
    }

    if ($PSCmdlet.ShouldProcess($fullPath, 'Write file')) {
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($fullPath, $Content.Trim(), $utf8NoBom)
    }
    return 'created'
}

#endregion

#region Resolve target
$target = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($TargetPath)
#endregion

#region Directories
$directories = @(
    # Source layout (Section C)
    'apps/agent_api',
    'apps/tools_api',
    'apps/web_ui',
    'packages/agent_core',
    'packages/rag',
    'packages/safety',
    'packages/eval',
    'packages/common/providers/contract_tests',
    'data/sops',
    'infra/bicep',
    'infra/scripts',
    'docs',
    # CI
    '.github/workflows',
    # AI tool dot-folders
    '.cursor/plans',
    '.cursor/rules',
    '.vscode',
    '.claude/commands',
    '.agents/rules',
    '.amazonq',
    '.continue',
    '.kiro/steering',
    '.kiro/specs'
)

if ($PSCmdlet.ShouldProcess($target, 'Initialize project')) {
    Ensure-Directory -Path $target
    foreach ($dir in $directories) {
        Ensure-Directory -Path (Join-Path $target $dir)
    }
}
#endregion

Write-Host "Initializing Servicing Agent skeleton at:" -ForegroundColor Cyan
Write-Host "  $target" -ForegroundColor Cyan
Write-Host ""

$stats = @{ created = 0; skipped = 0 }

#region File Manifest
function Get-InitFileManifest {
    return @(

        # â”€â”€ Root config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        @{
            Path = 'README.md'
            Content = @'
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

Read **`CLAUDE.md`** before generating or reviewing code.
Track work in **`TASKS.md`**; append session notes to **`logs.md`**.

## Layout

```
LoanOps Agent_Demos/
  apps/
    agent_api/      FastAPI /chat, /health, streaming, audit log
    tools_api/      FastAPI 5 mock servicing endpoints
    web_ui/         Streamlit rep UI
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
  local â†” Azure via env vars only. See `docs/01-servicing-agent-prompts.md` Â§A.6.1.
- **No PII in code or commits**. All loan data is synthetic.
- **Eval gate is sacred**: never weaken a threshold; fix the root cause instead.
'@
        },
        @{
            Path = 'Makefile'
            Content = @'
.PHONY: install lint test ingest eval demo down

install:
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy --strict packages

test:
	uv run pytest

ingest:
	uv run python -m packages.rag.ingest data/sops

eval:
	uv run python -m packages.eval.run --golden data/golden.jsonl --report out/eval.json

demo:
	uvicorn apps.tools_api.main:app --port 8001 &
	uvicorn apps.agent_api.main:app --port 8000 &
	uv run streamlit run apps/web_ui/app.py

down:
	pkill -f "uvicorn apps" || true
	pkill -f "streamlit run" || true
'@
        },
        @{
            Path = 'pyproject.toml'
            Content = @'
[project]
name = "servicing-agent"
version = "0.1.0"
description = "Servicing Agent for Internal Care Reps"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "agent-framework==1.5.0",
    "httpx>=0.27.0",
    "qdrant-client>=1.9.0",
    "sentence-transformers>=3.0.0",
    "presidio-analyzer>=2.2.35",
    "presidio-anonymizer>=2.2.35",
    "spacy>=3.7.0",
    "streamlit>=1.35.0",
    "ragas>=0.1.9",
    "opentelemetry-sdk>=1.25.0",
    "structlog>=24.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
    "pre-commit>=3.7.0",
]

[tool.ruff]
target-version = "py311"
line-length = 99

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
strict = true
python_version = "3.11"

[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = ["integration: requires live external services"]
'@
        },
        @{
            Path = '.env.example'
            Content = @'
# â”€â”€ Provider selections â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Swap local <-> Azure by changing the values below; no code changes needed.

LLM__PROVIDER=ollama
LLM__OLLAMA__BASE_URL=http://localhost:11434
LLM__OLLAMA__MODEL_FAST=llama3.1:8b
LLM__OLLAMA__MODEL_ACCURATE=llama3.1:8b
# LLM__PROVIDER=aoai
# LLM__AOAI__ENDPOINT=https://<resource>.openai.azure.com
# LLM__AOAI__DEPLOYMENT_FAST=gpt-4o-mini
# LLM__AOAI__DEPLOYMENT_ACCURATE=gpt-4o

EMBEDDING__PROVIDER=local_bge
# EMBEDDING__PROVIDER=aoai
# EMBEDDING__AOAI__ENDPOINT=https://<resource>.openai.azure.com
# EMBEDDING__AOAI__DEPLOYMENT=text-embedding-3-large

VECTOR_STORE__PROVIDER=qdrant
VECTOR_STORE__QDRANT__URL=http://localhost:6333
VECTOR_STORE__QDRANT__COLLECTION=sops
# VECTOR_STORE__PROVIDER=ai_search
# VECTOR_STORE__AI_SEARCH__ENDPOINT=https://<resource>.search.windows.net
# VECTOR_STORE__AI_SEARCH__INDEX=sops

PII__PROVIDER=presidio

SAFETY__PROVIDER=stub
# SAFETY__PROVIDER=azure
# SAFETY__AZURE__ENDPOINT=https://<resource>.cognitiveservices.azure.com

AUDIT__SINK=jsonl
AUDIT__JSONL__DIR=./audit
# AUDIT__SINK=appinsights
# AUDIT__APPINSIGHTS__CONNECTION_STRING=InstrumentationKey=...

SECRETS__PROVIDER=env
# SECRETS__PROVIDER=keyvault
# SECRETS__KEYVAULT__URI=https://<vault>.vault.azure.net

TELEMETRY__PROVIDER=console
# TELEMETRY__PROVIDER=appinsights
# TELEMETRY__APPINSIGHTS__CONNECTION_STRING=InstrumentationKey=...

TOOLS_CLIENT__PROVIDER=http
TOOLS_CLIENT__BASE_URL=http://localhost:8001
TOOLS_CLIENT__TOKEN=dev-token

PROMPT_STORE__PROVIDER=file
PROMPT_STORE__FILE__BASE_DIR=./docs
# PROMPT_STORE__PROVIDER=promptflow
# PROMPT_STORE__PROMPTFLOW__WORKSPACE=<workspace>
'@
        },
        @{
            Path = '.gitignore'
            Content = @'
# Secrets / env
.env
.env.local
.env.*.local
!.env.example

# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/
dist/
build/

# Tools
.pytest_cache/
.mypy_cache/
.ruff_cache/
.DS_Store
.idea/
*.log

# Project outputs
out/
audit/

# AI tool local state
.cursor/plans/*.plan.md
.claude/settings.local.json
'@
        },
        @{
            Path = '.pre-commit-config.yaml'
            Content = @'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-yaml
      - id: check-json
      - id: check-merge-conflict
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
'@
        },

        # â”€â”€ AI context docs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        @{
            Path = 'CLAUDE.md'
            Content = @'
# Servicing Agent â€” AI Agent Instructions

> Read this file before generating any code. Re-read Â§Tech stack and Â§Rules
> whenever you are about to make a design choice.

## What this project is

An **internal copilot for licensed mortgage-servicing care reps** at a US
mortgage servicer. Hybrid architecture: identical Python codebase runs
locally (Ollama + Qdrant) or on Azure (AOAI + AI Search) via env-var swap.
Full brief: `docs/01-servicing-agent-prompts.md`.

## Read order

| File | Purpose |
|------|---------|
| `CLAUDE.md` (this file) | Architecture & constraints |
| `TASKS.md` | Active work â€” check before starting |
| `decisions.md` | Settled ADRs |
| `docs/01-servicing-agent-prompts.md` | Full project brief (source of truth) |
| `packages/common/settings.py` | Every env var, single source |
| `packages/common/providers/` | Provider abstraction layer |

## Tech stack

| Layer | Local (dev) | Azure (target) |
|-------|-------------|----------------|
| Language | Python 3.11 | Python 3.11 |
| API framework | FastAPI | FastAPI on AKS |
| Orchestration | Microsoft Agent Framework | Same + Prompt Flow |
| LLM | Ollama Llama 3.1 8B | Azure OpenAI GPT-4o |
| Embeddings | bge-small-en-v1.5 | text-embedding-3-large |
| Vector store | Qdrant (Docker) | Azure AI Search |
| PII | Presidio | Presidio |
| Content safety | Rule-based stub | Azure AI Content Safety |
| Audit log | JSONL on disk | App Insights + ADLS |
| Observability | OTel to console | App Insights |
| Secrets | .env | Key Vault + Managed Identity |
| UI | Streamlit | App Service |

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

- **Local-first**: `make demo` must work with zero Azure credentials.
- **No concrete imports** outside `packages/common/providers/` â€” CI grep gate enforces this.
- **No `os.environ` / `os.getenv`** outside `packages/common/settings.py`.
- **No PII** anywhere in code, test fixtures, or commits. Use synthetic data.
- **No mutating tool calls** in v1 (no payments, no plan starts, no holds).
- **Eval gate is sacred**: never change a threshold downward. Fix the cause.
- **Every factual answer must have a citation** (`policy:` or `tool:` prefix).
- **uv** for all Python env management. Never raw `pip install`.
- **Async Python** throughout the backend.
- **mypy --strict** on all packages. No `Any` without an explicit `# type: ignore` comment explaining why.

## Module layout

```
apps/
  agent_api/    FastAPI :8000  /chat (SSE), /health, /version
  tools_api/    FastAPI :8001  5 mock servicing endpoints
  web_ui/       Streamlit rep UI

packages/
  agent_core/   Microsoft Agent Framework agent, prompt loader, intent router
  rag/          Chunker, ingest CLI, retrieval
  safety/       PII + content-safety middleware
  eval/         Ragas + custom metrics, golden runner, CI gate
  common/       Settings, schemas, Provider layer
```

## After each session

1. Mark completed items in `TASKS.md` (`- [ ]` â†’ `- [x]`)
2. Append a dated entry to `logs.md`
3. Update `decisions.md` for any new ADR
4. Update `docs/02-architecture.md` or `docs/03-eval-strategy.md` if relevant
'@
        },
        @{
            Path = 'GEMINI.md'
            Content = @'
# Servicing Agent â€” Gemini / Google AI Context

> Mirror of `CLAUDE.md` for Gemini-based tools.
> Keep in sync or point your tool directly at `CLAUDE.md`.

See `CLAUDE.md` for the full instruction set. Key points:

- Full brief: `docs/01-servicing-agent-prompts.md`
- Active tasks: `TASKS.md`
- Provider abstraction in `packages/common/providers/` â€” no concrete imports outside that folder.
- All env config via `packages/common/settings.py` only.
- Local-first. `make demo` must work with zero Azure credentials.
- Eval gate is sacred. Never lower a threshold.
'@
        },
        @{
            Path = 'TASKS.md'
            Content = @'
# Servicing Agent â€” Task Tracker

> **Current focus:** Step 1 â€” Repo skeleton

---

## Step 1 â€” Repo skeleton (acceptance: `make install lint test` exits 0)

- [ ] Configure `uv` workspace (`pyproject.toml` already stubbed)
- [ ] Wire `ruff`, `mypy --strict`, `pytest` via `pyproject.toml`
- [ ] Install and configure `pre-commit`
- [ ] Verify `make install lint test` exits 0 on clean clone

## Step 1.5 â€” Provider contracts (do before any feature work)

- [ ] `packages/common/settings.py` â€” full Pydantic Settings with nested provider configs
- [ ] `packages/common/providers/base.py` â€” ProviderHealth, ProviderError, ProviderCallEvent
- [ ] Implement Protocol + InMemory impl for all 10 provider categories
- [ ] `packages/common/providers/factory.py` â€” 10 factory functions, lru_cache
- [ ] `packages/common/providers/contract_tests/` â€” one test module per Protocol
- [ ] CI grep gate: no concrete imports outside providers/
- [ ] Accept: `mypy --strict packages/common` clean; contract tests green

## Step 2 â€” Synthetic data

- [ ] `data/loans.json` â€” 50 synthetic loans (CA/TX/FL/NY/OH mix)
- [ ] `data/sops/` â€” 30 synthetic markdown SOPs with YAML frontmatter
- [ ] `data/golden.jsonl` â€” 50 Q&A items (â‰¥5 refusal, â‰¥5 escalation)
- [ ] `python -m packages.eval.validate_data` reports 0 errors

## Step 3 â€” RAG pipeline

- [ ] `LocalBgeEmbeddingProvider` + `QdrantVectorStoreProvider`
- [ ] `AzureOpenAIEmbeddingProvider` + `AzureAISearchVectorStoreProvider`
- [ ] Chunker: ~600 tokens, 80 overlap, markdown header-aware
- [ ] `python -m packages.rag.ingest data/sops` ingests all SOPs
- [ ] Nearest-neighbour test: 10 known queries return correct chunk

## Step 4 â€” Tools API

- [ ] FastAPI :8001, 5 endpoints, Bearer auth
- [ ] Pydantic v2 response models matching Appendix signatures
- [ ] `pytest apps/tools_api/tests` green; `/docs` available

## Step 5 â€” Agent core

- [ ] Microsoft Agent Framework agent wired to `get_chat_provider()`
- [ ] System prompt loaded from `docs/01-servicing-agent-prompts.md` Â§B
- [ ] Intent router (pure function, no concrete provider import)
- [ ] JSON output contract enforced; retry once on schema failure
- [ ] Unit tests: happy / refuse / escalate paths against InMemory providers

## Step 6 â€” Agent API

- [ ] FastAPI :8000, `POST /chat` (SSE), `GET /health`, `GET /version`
- [ ] `GET /health` aggregates all 10 providers; 503 on failure
- [ ] Audit record written per turn via `get_audit_sink_provider()`
- [ ] No concrete provider imports in `apps/agent_api`

## Step 7 â€” Safety layer

- [ ] `PresidioPiiProvider` â€” SSN, DOB, account, name redaction
- [ ] `RuleBasedSafetyProvider` + `AzureContentSafetyProvider`
- [ ] Middleware: PII anonymize inbound, safety evaluate outbound
- [ ] Tests: redaction + blocking pass against both provider configs

## Step 8 â€” Eval harness

- [ ] Runner: `python -m packages.eval.run`
- [ ] Metrics: faithfulness â‰¥0.85, citation_coverage =1.0, refusal_correctness â‰¥0.95, p95 â‰¤4000ms
- [ ] CI fails on threshold breach; `make eval` seeded regression exits non-zero

## Step 9 â€” Streamlit rep UI

- [ ] Two-pane layout: borrower context | conversation
- [ ] Citations, tool trace, confidence, Approve & copy, Escalate
- [ ] `make demo` brings up full stack end-to-end

## Step 10 â€” IaC + CI

- [ ] Bicep modules: AOAI, AI Search, AKS, KV, MI, App Insights, Private Endpoints
- [ ] `ci.yml`: lint + mypy + unit tests on PR
- [ ] `eval-gate.yml`: nightly + PR; uploads `out/eval.json` artifact
'@
        },
        @{
            Path = 'decisions.md'
            Content = @'
# Servicing Agent â€” Architecture Decision Records

> Format: **Decision â†’ Context â†’ Alternatives â†’ Reasoning â†’ Status**

---

## ADR-001 â€” Orchestration: Microsoft Agent Framework

**Decision:** Use Microsoft Agent Framework as the primary orchestration framework.

**Context:** Need a Python-native orchestrator that integrates with Azure OpenAI
and supports production-grade agents, tool use, workflows, telemetry, and Azure deployment.

**Alternatives:** Previous brief default, LangChain.

**Reasoning:** Microsoft Agent Framework is the successor path for Microsoft agent
development, combining agent abstractions, tool orchestration, workflows, telemetry,
and Azure integration while preserving a clean provider boundary in this repo.

**Status:** Accepted â€” this overrides the original orchestration default in
`docs/01-servicing-agent-prompts.md`.

---

## ADR-002 â€” Local LLM: Ollama + Llama 3.1 8B

**Decision:** Use Ollama for local dev; no AOAI credentials required to run
`make demo`.

**Reasoning:** Zero-cost local dev, same code path as Azure via `ChatProvider`
Protocol.

**Status:** Accepted.

---

## ADR-003 â€” Rep UI: Streamlit

**Decision:** Streamlit for the internal rep UI.

**Reasoning:** Fastest path to a working two-pane layout for an internal tool.
Next.js is noted as a stretch in App.5.

**Status:** Accepted.

---

## ADR-004 â€” Provider Abstraction Pattern

**Decision:** All 10 external capabilities exposed as `typing.Protocol`
interfaces; concrete implementations selected at runtime from env vars.

**Reasoning:** Required for local-first / Azure-target hybrid without code forks.
See `docs/01-servicing-agent-prompts.md` Â§A.6.1 for full rationale.

**Status:** Accepted â€” load-bearing, do not modify without a new ADR.
'@
        },
        @{
            Path = 'logs.md'
            Content = @'
# Servicing Agent â€” Development Log

> Format: `## [YYYY-MM-DD] â€” Summary`

---

## [2026-05-21] â€” Project scaffolded

**Session type:** Scaffold

**Completed:**
- Ran `docs/Init-Project.ps1` â€” repo skeleton, provider stubs, AI dot-folders, context docs

**Next:** Step 1 â€” wire `uv`, `ruff`, `mypy`, `pytest`; verify `make install lint test` exits 0.
'@
        },
        @{
            Path = 'notes.md'
            Content = @'
# Servicing Agent â€” Notes

> Links, research, and scratch ideas â€” not a spec.

## Useful references

- Project brief: `docs/01-servicing-agent-prompts.md`
- Ragas docs: https://docs.ragas.io
- Microsoft Agent Framework: https://learn.microsoft.com/en-us/agent-framework/overview/
- Presidio: https://microsoft.github.io/presidio/
- Qdrant Python client: https://python-client.qdrant.tech/
- Azure AI Search hybrid: https://learn.microsoft.com/en-us/azure/search/hybrid-search-overview
'@
        },
        @{
            Path = 'scratchpad.md'
            Content = @'
# Servicing Agent â€” Scratchpad

> Temporary ideas. Safe to clear. AI agents may ignore this file.
'@
        },
        @{
            Path = 'context.md'
            Content = @'
# Servicing Agent â€” Quick Reference

> Where things go â€” companion to `CLAUDE.md`.

| What | Where |
|------|-------|
| Agent system prompt | `docs/01-servicing-agent-prompts.md` Â§B |
| Env vars / config | `packages/common/settings.py` |
| Provider Protocols | `packages/common/providers/<name>.py` |
| Provider factories | `packages/common/providers/factory.py` |
| InMemory providers (tests) | `packages/common/providers/testing.py` |
| Contract tests | `packages/common/providers/contract_tests/` |
| Shared Pydantic models | `packages/common/schemas.py` |
| Servicing tool endpoints | `apps/tools_api/` |
| Agent API (`/chat`, `/health`) | `apps/agent_api/` |
| RAG ingest CLI | `packages/rag/ingest.py` |
| Safety middleware | `packages/safety/` |
| Eval runner + metrics | `packages/eval/` |
| Golden Q&A set | `data/golden.jsonl` |
| Synthetic SOPs | `data/sops/` |
| Synthetic loans | `data/loans.json` |
| Azure IaC | `infra/bicep/` |
'@
        },

        # â”€â”€ .cursor â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        @{
            Path = '.cursor/rules/project.mdc'
            Content = @'
---
description: Servicing Agent project rules for Cursor
globs: ["**/*.py", "**/*.toml", "**/*.yaml", "**/*.yml"]
alwaysApply: true
---

# Servicing Agent â€” Cursor Rules

- Read `CLAUDE.md` before generating code.
- Never import concrete provider classes outside `packages/common/providers/`.
- Never read env vars outside `packages/common/settings.py`.
- All Python must pass `mypy --strict`. No bare `Any`.
- Use `uv run` for all Python invocations (never raw `python` or `pip`).
- No PII in any file. All loan/borrower data must be synthetic.
- Eval thresholds in `packages/eval/` are immutable â€” never lower them.
'@
        },

        # â”€â”€ .vscode â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        @{
            Path = '.vscode/settings.json'
            Content = @'
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  },
  "mypy-type-checker.args": ["--strict"],
  "files.exclude": {
    "**/__pycache__": true,
    "**/.mypy_cache": true,
    "**/.ruff_cache": true
  }
}
'@
        },
        @{
            Path = '.vscode/extensions.json'
            Content = @'
{
  "recommendations": [
    "charliermarsh.ruff",
    "ms-python.mypy-type-checker",
    "ms-python.python",
    "ms-python.vscode-pylance",
    "tamasfe.even-better-toml"
  ]
}
'@
        },

        # â”€â”€ .claude â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        @{
            Path = '.claude/commands/build-step.md'
            Content = @'
# /build-step

Execute a single numbered build step from the project brief.

**Usage:** `/build-step <n>` â€” e.g. `/build-step 1.5`

**Before starting:**
1. Read `CLAUDE.md`
2. Read `TASKS.md` â€” confirm step is not already done
3. Read `docs/01-servicing-agent-prompts.md` Â§C for the step''s acceptance criteria

**After completing:**
1. Mark tasks done in `TASKS.md`
2. Append entry to `logs.md`
3. Confirm acceptance criteria pass before returning
'@
        },
        @{
            Path = '.claude/commands/check-providers.md'
            Content = @'
# /check-providers

Verify the Provider Abstraction invariants hold across the codebase.

1. `grep -R "from packages.common.providers.*import.*Provider" apps/ packages/agent_core packages/rag packages/safety packages/eval` â€” must return zero matches for concrete classes.
2. `grep -RnE "os\.environ|os\.getenv" --include="*.py" .` excluding `settings.py` and `tests/` â€” must be empty.
3. Run `pytest packages/common/providers/contract_tests` â€” all green.
4. Run `mypy --strict packages/common` â€” no errors.
'@
        },

        # â”€â”€ .agents â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        @{
            Path = '.agents/rules/servicing-agent.md'
            Content = @'
# Servicing Agent â€” Agent Rules

These rules apply to all AI agents working on this codebase.

## Mandatory reads (in order)
1. `CLAUDE.md`
2. `TASKS.md`
3. `decisions.md`
4. `docs/01-servicing-agent-prompts.md` (full brief when making design choices)

## Hard constraints
- No concrete provider imports outside `packages/common/providers/`
- No `os.environ` / `os.getenv` outside `packages/common/settings.py`
- No PII â€” synthetic data only
- No mutating tool calls in v1
- Eval thresholds are immutable â€” never lower them

## Approval required before
- New ADR / architecture change
- New environment variables
- Schema-breaking migrations
- Changing any eval threshold
- Adding a new external capability (must add a Provider Protocol first)
'@
        },

        # â”€â”€ .kiro â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        @{
            Path = '.kiro/steering/project.md'
            Content = @'
# Servicing Agent â€” Kiro Steering

## Goal
Build a hybrid (local-first, Azure-deployable) copilot for mortgage-servicing
care reps. Full brief: `docs/01-servicing-agent-prompts.md`.

## Key files
- `CLAUDE.md` â€” architecture & constraints
- `TASKS.md` â€” current work items
- `packages/common/providers/` â€” Provider Abstraction layer

## Non-negotiables
- Local-first: zero Azure credentials for `make demo`
- Provider Abstraction: no concrete imports outside `packages/common/providers/`
- Eval gate: never lower thresholds
'@
        },

        # â”€â”€ Provider stubs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        @{
            Path = 'packages/common/settings.py'
            Content = @'
"""Single source of truth for all configuration.

All application code reads config from Settings(). No direct os.environ calls
outside this module.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OllamaChatConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    model_fast: str = "llama3.1:8b"
    model_accurate: str = "llama3.1:8b"


class AOAIChatConfig(BaseModel):
    endpoint: str = ""
    deployment_fast: str = "gpt-4o-mini"
    deployment_accurate: str = "gpt-4o"
    api_version: str = "2024-08-01-preview"


class ChatConfig(BaseModel):
    provider: Literal["ollama", "aoai"] = "ollama"
    ollama: OllamaChatConfig = Field(default_factory=OllamaChatConfig)
    aoai: AOAIChatConfig | None = None
    deterministic_by_default: bool = False


class QdrantConfig(BaseModel):
    url: str = "http://localhost:6333"
    collection: str = "sops"


class AISearchConfig(BaseModel):
    endpoint: str = ""
    index: str = "sops"


class VectorStoreConfig(BaseModel):
    provider: Literal["qdrant", "ai_search"] = "qdrant"
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    ai_search: AISearchConfig | None = None


class EmbeddingConfig(BaseModel):
    provider: Literal["local_bge", "aoai"] = "local_bge"


class PiiConfig(BaseModel):
    provider: Literal["presidio"] = "presidio"


class SafetyConfig(BaseModel):
    provider: Literal["stub", "azure"] = "stub"


class AuditConfig(BaseModel):
    sink: Literal["jsonl", "appinsights"] = "jsonl"
    jsonl_dir: str = "./audit"


class SecretsConfig(BaseModel):
    provider: Literal["env", "keyvault"] = "env"


class TelemetryConfig(BaseModel):
    provider: Literal["console", "appinsights"] = "console"


class ToolsClientConfig(BaseModel):
    provider: Literal["http", "http_mtls"] = "http"
    base_url: str = "http://localhost:8001"
    token: str = "dev-token"


class PromptStoreConfig(BaseModel):
    provider: Literal["file", "promptflow"] = "file"
    file_base_dir: str = "./docs"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="forbid",
        case_sensitive=False,
    )

    llm: ChatConfig = Field(default_factory=ChatConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    pii: PiiConfig = Field(default_factory=PiiConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    secrets: SecretsConfig = Field(default_factory=SecretsConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    tools_client: ToolsClientConfig = Field(default_factory=ToolsClientConfig)
    prompt_store: PromptStoreConfig = Field(default_factory=PromptStoreConfig)
'@
        },
        @{ Path = 'packages/common/schemas.py'
           Content = '# Shared Pydantic models (AgentTurnOutput, LoanSummary, etc.)' },
        @{ Path = 'packages/common/__init__.py'; Content = '' },
        @{ Path = 'packages/common/providers/__init__.py'
           Content = '# Re-exports: Protocols and get_*_provider() factories only. No concrete classes.' },
        @{ Path = 'packages/common/providers/base.py'
           Content = '# ProviderHealth, ProviderError, ProviderConfigError, ProviderCallEvent, ModelHint' },
        @{ Path = 'packages/common/providers/factory.py'
           Content = '# get_chat_provider(), get_embedding_provider(), get_vector_store_provider(), ...' },
        @{ Path = 'packages/common/providers/chat.py'
           Content = '# ChatProvider Protocol + OllamaChatProvider + AzureOpenAIChatProvider' },
        @{ Path = 'packages/common/providers/embedding.py'
           Content = '# EmbeddingProvider Protocol + LocalBgeEmbeddingProvider + AzureOpenAIEmbeddingProvider' },
        @{ Path = 'packages/common/providers/vector_store.py'
           Content = '# VectorStoreProvider Protocol + QdrantVectorStoreProvider + AzureAISearchVectorStoreProvider' },
        @{ Path = 'packages/common/providers/pii.py'
           Content = '# PiiProvider Protocol + PresidioPiiProvider' },
        @{ Path = 'packages/common/providers/content_safety.py'
           Content = '# ContentSafetyProvider Protocol + RuleBasedSafetyProvider + AzureContentSafetyProvider' },
        @{ Path = 'packages/common/providers/audit_sink.py'
           Content = '# AuditSinkProvider Protocol + JsonlAuditSinkProvider + AppInsightsAuditSinkProvider' },
        @{ Path = 'packages/common/providers/secrets.py'
           Content = '# SecretsProvider Protocol + EnvFileSecretsProvider + KeyVaultSecretsProvider' },
        @{ Path = 'packages/common/providers/telemetry.py'
           Content = '# TelemetryProvider Protocol + ConsoleOtelTelemetryProvider + AppInsightsTelemetryProvider' },
        @{ Path = 'packages/common/providers/tools_client.py'
           Content = '# ToolsClientProvider Protocol + HttpToolsClientProvider (+ mTLS variant)' },
        @{ Path = 'packages/common/providers/prompt_store.py'
           Content = '# PromptStoreProvider Protocol + FilePromptStoreProvider + PromptFlowPromptStoreProvider' },
        @{ Path = 'packages/common/providers/testing.py'
           Content = '# InMemoryChatProvider, InMemoryVectorStoreProvider, etc. for unit tests' },
        @{ Path = 'packages/common/providers/contract_tests/__init__.py'; Content = '' },

        # â”€â”€ Package __init__ stubs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        @{ Path = 'packages/__init__.py'; Content = '' },
        @{ Path = 'packages/agent_core/__init__.py'; Content = '' },
        @{ Path = 'packages/rag/__init__.py'; Content = '' },
        @{ Path = 'packages/safety/__init__.py'; Content = '' },
        @{ Path = 'packages/eval/__init__.py'; Content = '' },
        @{ Path = 'apps/__init__.py'; Content = '' },
        @{ Path = 'apps/agent_api/__init__.py'; Content = '' },
        @{ Path = 'apps/tools_api/__init__.py'; Content = '' },

        # â”€â”€ Synthetic data placeholders â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        @{ Path = 'data/loans.json'; Content = '[]' },
        @{ Path = 'data/golden.jsonl'; Content = '' },

        # â”€â”€ GitHub Actions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        @{
            Path = '.github/workflows/ci.yml'
            Content = @'
name: CI

on:
  push:
  pull_request:

jobs:
  lint-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          python-version: "3.11"
      - run: uv sync --all-extras
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy --strict packages
      - run: uv run pytest -x

  provider-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: No concrete provider imports outside providers/
        run: |
          matches=$(git grep -nE "from packages\.common\.providers\.[a-z_]+_impls?\.[a-z_]+ import" -- \
            ":!packages/common/providers" || true)
          if [ -n "$matches" ]; then
            echo "Direct concrete-provider imports detected:"; echo "$matches"; exit 1
          fi
      - name: No direct env reads outside settings.py
        run: |
          env_reads=$(git grep -nE "os\.environ|os\.getenv" -- \
            ":!packages/common/settings.py" ":!**/tests/**" || true)
          if [ -n "$env_reads" ]; then
            echo "Direct env access detected:"; echo "$env_reads"; exit 1
          fi
'@
        },
        @{
            Path = '.github/workflows/eval-gate.yml'
            Content = @'
name: Eval Gate

on:
  pull_request:
  schedule:
    - cron: "0 0 * * *"

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          python-version: "3.11"
      - run: uv sync --all-extras
      - name: Run eval
        run: uv run python -m packages.eval.run --golden data/golden.jsonl --report out/eval.json
      - name: Upload eval report
        uses: actions/upload-artifact@v4
        with:
          name: eval-report
          path: out/eval.json
'@
        }
    )
}
#endregion

foreach ($item in (Get-InitFileManifest)) {
    $result = Write-InitFile -Root $target -RelativePath $item.Path -Content $item.Content
    if ($result -eq 'created') { $stats.created++ } elseif ($result -eq 'skipped') { $stats.skipped++ }
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "  Created : $($stats.created)"
Write-Host "  Skipped : $($stats.skipped)"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. cd `"$target`""
Write-Host "  2. cp .env.example .env"
Write-Host "  3. make install"
Write-Host "  4. make lint test"
Write-Host ""
