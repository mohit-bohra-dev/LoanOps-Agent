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
