## [2026-09-29] — ADR-010 One modular Python product

**Session type:** Architecture / module scaffold

**Completed:**
- ADR-010: Python-only backend, provider_contracts, duplicate keep/remove table.
- provider_contracts: `BedrockEmbeddingProvider`, session_store ABC + memory/mock/postgres.
- LoanOps modules: `packages/sse`, `packages/db`, `packages/docs`, `packages/wiki`.
- ModularToolsClient + scopes; Agent API `/mcp/tools`, `/mcp/keys`.
- Settings: `SSE__*`, `SQL_SERVER__*`, session postgres, vector pgvector, tools=modular.
- Docs: `docs/RETIRE_STANDALONE.md`. SQL driver = aioodbc + ODBC 18.
- Embedding: local bge-small; AWS Titan embed v2 1024-dim.

**Reason:** Single product for users/agents querying SSE APIs + docs; retire Node gateway and standalone wiki after parity.

---

## [2026-07-24] — Independent DATA__LOAN_SOURCE / DATA__SOP_SOURCE

**Session type:** Config / provider wiring

**Completed:**
- Split loan vs SOP selection: `DATA__LOAN_SOURCE`, `DATA__SOP_SOURCE`,
  `DATA__SOP_CONFLUENCE_MODE` (cache|live).
- Factory wires Confluence-only via `_confluence` cache or live API.
- Deprecated `DATA__MODE` with backcompat mapping; ADR-009.
- `.env` demo mix: mock fixtures + Confluence-only cache.

**Reason:** Use ingested Confluence SOPs without synthetic local SOPs while
keeping loan fixtures offline.

---

## [2026-07-21] — Live Confluence SOP ingest (Escrow + Hardship)

**Session type:** Feature implementation

**Completed:**
- Implemented `ConfluencePolicyProvider` (REST v2, markitdown HTML→md, regex/presidio scrub, local artifact write).
- Added `CompositePolicyProvider`; `DATA__MODE=real` = local dummy SOPs + Confluence (add, not replace).
- Extended `ConfluenceConfig` with `page_ids`, `ancestor_ids`, `expand_children`, `pii_scrub`, `artifact_dir`.
- `LocalFilePolicyProvider` skips `_`-prefixed dirs so Confluence cache is not double-ingested.
- Gitignored `data/sops/_confluence/`; documented seed page IDs in `.env.example`.
- Unit tests for skip/composite/scrub; ADR-008.

**Reason:** Feed curated real SC-space Escrow/Hardship SOPs into RAG without committing confidential content or breaking offline `make demo`.

---

## [2026-06-21] — Langfuse Telemetry Integration

**Session type:** Feature implementation

**Completed:**
- Created `LangfuseTelemetryProvider` in `provider-contracts` using official Langfuse Python SDK.
- Wired provider into `factory.py` with `TELEMETRY__PROVIDER=langfuse`.
- Added configuration to `settings.py` (keys, host, optional).
- Updated eval harness (`run.py`) to push custom scores (citation coverage, refusal correctness, latency) to Langfuse.
- Added `docker-compose.langfuse.yml` for local self-hosting.
- Fixed 6 review issues (imports, lazy load, test mock, dummy traces, etc.).

**Reason:** Needed a dedicated eval UI/dashboard for OTel traces and metrics, per approved implementation plan.

---

## [2026-06-18] — Fix EscrowBalance Field Collision
**Session type:** Bug fix

**Completed:**
- Renamed `current_balance_usd` to `escrow_balance_usd` inside the `EscrowBreakdown` schema (`packages/common/schemas.py`).
- Updated `apps/tools_api/main.py` to use `escrow_balance_usd` in all `get_escrow_breakdown` tool return paths.
- Updated the testing mock data (`packages/agent_core/tests/conftest.py`) and documentation (`docs/01-servicing-agent-prompts.md`) to reflect the new `escrow_balance_usd` key.
- Kept `LoanSummary.current_balance_usd` intact, ensuring principal loan balance remains accurately represented.

**Reason:** The LLM was hallucinating because the `EscrowBreakdown` and `LoanSummary` schemas previously shared the exact same field name (`current_balance_usd`). The agent mistakenly used the $0.00 escrow account balance as the principal loan balance when answering queries. Disambiguating the field name prevents this collision.

---

## [2026-06-18] — Bedrock API Key Auth & PII Stub Fixes

**Session type:** Bug fix

**Completed:**
- Added a `stub` mode for the `PiiProvider` (`MockPiiProvider`) via `settings.py` and `factory.py` to fix slow local startup times caused by Presidio/spaCy loading.
- Fixed Bedrock's `Converse` API integration returning blank responses by mapping non-compliant roles (`tool`, `function`) to `user` and throwing explicit errors if the `messages` array is empty.
- Fixed Bedrock API key authentication (bearer token mode) by properly setting `os.environ["AWS_BEARER_TOKEN_BEDROCK"]` and using `bedrock-runtime.{region}` instead of forcing it through `aws_session_token`.
- Added verbose `logging` to `BedrockProvider.chat()` for easier diagnostics.

**Reason:** Agent API took 10-15s to start, and Bedrock was returning silent blanks due to malformed payload roles and incorrect AWS IAM header injection.

---

## [2026-06-10] — Conversational Memory Feature

**Session type:** Feature implementation

**Completed:**
- Added `SessionStoreProvider` and `InMemorySessionStoreProvider` to `provider_contracts` and `packages/common/providers`.
- Implemented sliding window memory strategy in `packages/agent_core/_memory.py`.
- Integrated memory state into `/chat` API loop using the session store.
- Updated `ChatPane.tsx` to handle dynamic session IDs, pass active `loan_id`, and added a "New Chat" button.
- Lifted `activeLoanId` state in `App.tsx` and updated `BorrowerContextPane.tsx` to invoke `onLoanLoaded`.
- Created tests for memory logic (`test_memory.py`) and contracts (`test_contract.py`). All tests pass.

**Reason:** Added conversational memory capabilities with context expiration per the newly approved implementation plan.

---

## [2026-06-09] — Graphify-first rule added to all agent instructions

**Session type:** Tooling / agent workflow

**Completed:**
- Added `§Knowledge graph (Graphify) — mandatory` section to both `AGENTS.md` and `GEMINI.md`
- Added `Graphify-first` as the first non-negotiable rule in both files
- Added `graphify-out/graph.json` to the Read order table
- Updated "Build a step" workflow: step 2 now runs `graphify query`, step 6 runs `graphify update .`
- Coverage: Cursor (`.cursor/rules/graphify.mdc`), Gemini (`GEMINI.md`), Copilot/others (`AGENTS.md`)

**Reason:** Graphify graph existed but only the Cursor `.mdc` rule referenced it. Other agentic IDEs (Gemini, Copilot, Windsurf) had no instruction to use the knowledge graph, leading to redundant grep/file-reads.

---

## [2026-06-09] — Fix Safety Middleware Showstopper

**Session type:** Bug fix / Implementation

**Completed:**
- Wired up `SafetyPipeline.sanitize_inbound` to the `/chat` endpoint in `apps/agent_api/main.py`.
- Wired up `SafetyPipeline.evaluate_outbound` to the agent response.
- Removed Step 7 TODO from `apps/agent_api/models.py`.
- Updated test mocks in `apps/agent_api/tests/test_agent_api.py` to properly mock async middleware calls.
- Reviewed conversation memory architecture plan.

**Reason:** PII was going unredacted into the audit log and the `run_agent_turn` function. Outbound safety checks were also skipped.

---

## [2026-06-08] — Fix mypy test monkeypatch signatures

**Session type:** Bug fix

**Completed:**
- Fixed `packages/agent_core/tests/test_agent_core.py` patch signatures for `patched_chat`, `failing_then_valid`, `always_fails`
- Updated signatures to include `self`, `json_mode: bool`, and return `LLMResponse`
- Used `MethodType` to bind local async functions to `MockLLMProvider`
- Updated `# type: ignore[assignment]` → `# type: ignore[method-assign]`
- Verified `make lint` now passes (ruff + mypy)

**Reason:** Mypy error caused by incompatible callable shape (missing `self` + missing `json_mode`).

---

## [2026-09-29] — Docs sync: tools_api retired

Updated ARCHITECTURE, PRD, ANALYSIS, CONTEXT, demo/query docs, and STEP 4 in
`docs/01-servicing-agent-prompts.md` to match SSE-only runtime (ADR-010).

---

## [2026-09-29] — Remove tools_api; SSE-only answer path

**Session type:** Cleanup / architecture follow-through (ADR-010)

**Completed:**
- Deleted `apps/tools_api` (mock HTTP :8001)
- `TOOLS_CLIENT__PROVIDER=modular` only; dropped `TOOLS_API_TOKEN` / http tools client
- Removed helix `lookup_loan` scopes; system/care_rep = SSE + docs
- Web UI: Vite `/tools` proxy gone; `lookupLoan` → Agent MCP `call_sse_api`
- Docs: README, AGENTS, CONTEXT, RETIRE_STANDALONE, decisions ADR-010 note

**Next:** Optional commit/push; more `SSE__SWAGGER_LINKS` apps.

---

## [2026-05-31] — Tooling: Graphify knowledge graph

**Session type:** Tooling / developer experience

**Completed:**
- Installed Graphify CLI globally via `uv tool install graphifyy --with openai`
- Registered project-scoped Cursor skill (`graphify cursor install --project`) → `.cursor/rules/graphify.mdc` (`alwaysApply: true`)
- Added `.graphifyignore` (excludes `.venv/`, `node_modules/`, `.env`, `graphify-out/`, etc.)
- Built initial graph: 83 code files + 62 docs → `graphify-out/graph.json`
- Installed git post-commit / post-checkout hooks for auto-rebuild (AST-only, no API cost)
- `.gitignore`: ignore local-only `graphify-out/manifest.json`, `cost.json`, `cache/`
- Docs: added `GRAPHIFY_SETUP.md`; added §19 to `CONTEXT.md`
- Verified `graphify query "..."` returns scoped subgraphs

**Note:** Backend defaults to `gemini`; semantic extraction of docs/PDFs needs an API key for headless `graphify extract`. Code extraction is local (tree-sitter, no API calls).

**Next:** Step 8 eval harness is marked done in `TASKS.md`; remaining work is Step 10 (IaC + CI) and the Step 1.5 CI grep gate for concrete imports.

---

## [2026-05-28] — Step 7: Safety layer implemented

**Session type:** Implementation

**Completed:**
- Middleware: PII anonymize inbound, safety evaluate outbound
- Tests: redaction + blocking pass against both provider configs

**Next:** Step 8 — Eval harness. FastAPI :8000, `POST /chat` (SSE), `GET /health`, `GET /version`.
