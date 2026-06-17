# Servicing Agent â€” Task Tracker

> **Current focus:** Step 3 â€” RAG pipeline

---

## Step 1 â€” Repo skeleton (acceptance: `make install lint test` exits 0)

- [x] Configure `uv` workspace (`pyproject.toml` already stubbed)
- [x] Wire `ruff`, `mypy --strict`, `pytest` via `pyproject.toml`
- [x] Install and configure `pre-commit`
- [x] Verify `make install lint test` exits 0 on clean clone

## Step 1.5 â€” Provider contracts (do before any feature work)

- [x] `packages/common/settings.py` â€” full Pydantic Settings with nested provider configs
- [x] `packages/common/providers/base.py` â€” ProviderHealth, ProviderError, ProviderCallEvent
- [x] Implement Protocol + InMemory impl for all 10 provider categories
- [x] `packages/common/providers/factory.py` â€” 10 factory functions, lru_cache
- [x] `packages/common/providers/contract_tests/` â€” one test module per Protocol
- [ ] CI grep gate: no concrete imports outside providers/
- [x] Accept: `mypy --strict packages/common` clean; contract tests green

## Step 2 â€” Synthetic data

- [x] `data/loans.json` â€” 50 synthetic loans (CA/TX/FL/NY/OH mix)
- [x] `data/sops/` â€” 30 synthetic markdown SOPs with YAML frontmatter
- [x] `data/golden.jsonl` â€” 50 Q&A items (â‰¥5 refusal, â‰¥5 escalation)
- [x] `python -m packages.eval.validate_data` reports 0 errors

## Step 3 â€” RAG pipeline

- [x] `LocalBgeEmbeddingProvider` + `QdrantVectorStoreProvider`
- [x] `AzureOpenAIEmbeddingProvider` + `AzureAISearchVectorStoreProvider`
- [x] Chunker: ~600 tokens, 80 overlap, markdown header-aware
- [x] `python -m packages.rag.ingest data/sops` ingests all SOPs
- [x] Nearest-neighbour test: 10 known queries return correct chunk

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

## Step 6 â€” Agent API

- [x] FastAPI :8000, `POST /chat` (SSE), `GET /health`, `GET /version`
- [x] `GET /health` aggregates all 10 providers; 503 on failure
- [x] Audit record written per turn via `get_audit_sink_provider()`
- [x] No concrete provider imports in `apps/agent_api`

## Step 7 — Safety layer

- [x] `PresidioPiiProvider` — SSN, DOB, account, name redaction
- [x] `RuleBasedSafetyProvider` + `AzureContentSafetyProvider`
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

- [x] Bicep modules: AOAI, AI Search, AKS, KV, MI, App Insights, Private Endpoints
- [x] `ci.yml`: lint + mypy + unit tests on PR
- [x] `eval-gate.yml`: nightly + PR; uploads `out/eval.json` artifact

## Step 11 — Conversational Memory (Feature)

- [x] Session store abstraction (InMemory impl)
- [x] Background TTL cleanup task
- [x] Agent core memory strategy (Sliding window)
- [x] API integration with session context
- [x] UI updates to handle session IDs and active loan mapping
