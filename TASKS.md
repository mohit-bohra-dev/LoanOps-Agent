# Servicing Agent — Task Tracker

> **Current focus:** Step 12 — Observability & Eval Dashboard

---

## Step 1 — Repo skeleton (acceptance: `make install lint test` exits 0)

- [x] Configure `uv` workspace (`pyproject.toml` already stubbed)
- [x] Wire `ruff`, `mypy --strict`, `pytest` via `pyproject.toml`
- [x] Install and configure `pre-commit`
- [x] Verify `make install lint test` exits 0 on clean clone

## Step 1.5 — Provider contracts (do before any feature work)

- [x] `packages/common/settings.py` — full Pydantic Settings with nested provider configs
- [x] `packages/common/providers/base.py` — ProviderHealth, ProviderError, ProviderCallEvent
- [x] Implement Protocol + InMemory impl for all 10 provider categories
- [x] `packages/common/providers/factory.py` — 10 factory functions, lru_cache
- [x] `packages/common/providers/contract_tests/` — one test module per Protocol
- [ ] CI grep gate: no concrete imports outside providers/
- [x] Accept: `mypy --strict packages/common` clean; contract tests green

## Step 2 — Synthetic data

- [x] `data/loans.json` — 50 synthetic loans (CA/TX/FL/NY/OH mix)
- [x] `data/sops/` — 30 synthetic markdown SOPs with YAML frontmatter
- [x] `data/golden.jsonl` — 50 Q&A items (≥5 refusal, ≥5 escalation)
- [x] `python -m packages.eval.validate_data` reports 0 errors

## Step 3 — RAG pipeline

- [x] `LocalBgeEmbeddingProvider` + `QdrantVectorStoreProvider`
- [x] `AWSOpenAIEmbeddingProvider` + `AWSAISearchVectorStoreProvider`
- [x] Chunker: ~600 tokens, 80 overlap, markdown header-aware
- [x] `python -m packages.rag.ingest data/sops` ingests all SOPs
- [x] Nearest-neighbour test: 10 known queries return correct chunk
- [x] `ConfluencePolicyProvider` live ingest (Escrow + Hardship seeds)
- [x] `CompositePolicyProvider` — local dummy + Confluence when `DATA__MODE=real`
- [x] Gitignored local markdown artifacts under `data/sops/_confluence/`

## Step 4 — Tools API

- [x] FastAPI :8001, 5 endpoints, Bearer auth
- [x] Pydantic v2 response models matching Appendix signatures
- [x] `pytest apps/tools_api/tests` green; `/docs` available

## Step 5 — Agent core

- [x] Microsoft Agent Framework agent wired to `get_chat_provider()`
- [x] System prompt loaded from `docs/01-servicing-agent-prompts.md` §B
- [x] Intent router (pure function, no concrete provider import)
- [x] JSON output contract enforced; retry once on schema failure
- [x] Unit tests: happy / refuse / escalate paths against InMemory providers
- [x] Fix test monkeypatches to match protocol signature (self, json_mode)

## Step 6 — Agent API

- [x] FastAPI :8000, `POST /chat` (SSE), `GET /health`, `GET /version`
- [x] `GET /health` aggregates all 10 providers; 503 on failure
- [x] Audit record written per turn via `get_audit_sink_provider()`
- [x] No concrete provider imports in `apps/agent_api`

## Step 7 — Safety layer

- [x] `PresidioPiiProvider` — SSN, DOB, account, name redaction
- [x] `RuleBasedSafetyProvider` + `AWSContentSafetyProvider`
- [x] Middleware: PII anonymize inbound, safety evaluate outbound
- [x] Tests: redaction + blocking pass against both provider configs

## Step 8 — Eval harness

- [x] Runner: `python -m packages.eval.run`
- [x] Metrics: faithfulness >=0.85, citation_coverage =1.0, refusal_correctness >=0.95, p95 <=4000ms
- [x] CI fails on threshold breach; `make eval` seeded regression exits non-zero

## Step 9 — React + TypeScript rep UI

- [x] Two-pane layout: borrower context | conversation
- [x] Citations, tool trace, confidence, Approve & copy, Escalate
- [x] `make demo` brings up full stack end-to-end

## Step 10 — IaC + CI

- [x] Terraform modules: Bedrock, AI Search, ECS Fargate, KV, MI, CloudWatch Logs, Private Endpoints
- [x] `ci.yml`: lint + mypy + unit tests on PR
- [x] `eval-gate.yml`: nightly + PR; uploads `out/eval.json` artifact

## Step 11 — Conversational Memory (Feature)

- [x] Session store abstraction (InMemory impl)
- [x] Background TTL cleanup task
- [x] Agent core memory strategy (Sliding window)
- [x] API integration with session context
- [x] UI updates to handle session IDs and active loan mapping

## Step 12 — Observability & Eval Dashboard

- [x] Implement `LangfuseTelemetryProvider` in `provider-contracts`
- [x] Wire Langfuse into `LoanOps-Agent` settings and factory
- [x] Push eval metrics to Langfuse dashboard from `run_eval`
- [x] Provide `docker-compose.langfuse.yml` for self-hosted instance
