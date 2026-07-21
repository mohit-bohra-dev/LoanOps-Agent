# Graph Report - LoanOps-Agent  (2026-07-16)

## Corpus Check
- 179 files · ~90,760 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2915 nodes · 5779 edges · 496 communities (233 shown, 263 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 590 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `660794ed`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 49
- Community 50
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 151
- Community 152
- Community 153
- Community 154
- Community 155
- Community 156
- Community 157
- Community 158
- Community 159
- Community 160
- Community 161
- Community 162
- Community 163
- Community 164
- Community 165
- Community 166
- Community 167
- Community 168
- Community 169
- Community 170
- Community 171
- Community 172
- Community 173
- Community 174
- Community 175
- Community 176
- Community 177
- Community 178
- Community 181
- Community 182
- Community 183
- Community 184
- Community 185
- Community 186
- Community 187
- Community 189
- Community 191
- Community 192
- Community 193
- Community 194
- Community 195
- Community 197
- Community 200
- Community 201
- Community 207
- Community 210
- Community 219
- servicing-agent
- uy
- Nm
- 14. Delivery Phasing & Milestones
- test_no_direct_env_access
- eslint
- ax
- AbstractSessionStoreProvider
- Health status of a single provider.
- Aggregated health response for all providers.
- Audit payload stored per agent turn.      Matches the spec: turn_id, rep_id, pro
- Execute tool calls and return recorded items.      If *pii_token_map* is provide
- Run a single agent turn and return structured output.
- Build history messages from a session using a sliding window strategy.      Stra
- Raised when the LLM output cannot be parsed into ``AgentTurnOutput``.
- Try to extract a JSON object from the LLM response.      Handles cases where t
- apps/agent_api/
- int
- str
- Aggregate health of all 10 providers; 503 on any failure.
- Aggregate health of all 10 providers; 503 on any failure.
- Return the current API version.
- Return the current API version.
- Handle a chat turn and stream the result as SSE.      The agent output is comput
- Handle a chat turn and stream the result as SSE.      The agent output is comp
- # TODO: Step 7 — PII redact prompt before storing in audit
- Snapshot which concrete provider is bound for each category.      Returns a di
- Snapshot which concrete provider is bound for each category.      Returns a di
- Snapshot which concrete provider is bound for each category.      Returns a di
- Snapshot which concrete provider is bound for each category.      Returns a di
- Retrieve the chat memory for a given session, showing which turns are active/ina
- Retrieve the chat memory for a given session, showing which turns are active/ina
- Retrieve the chat memory for a given session, showing which turns are active/ina
- Application lifespan: flush audit sink on shutdown.
- Health status of a single provider.
- Aggregated health response for all providers.
- Audit payload stored per agent turn.      Matches the spec: turn_id, rep_id, pro
- MagicMock
- str
- Verify apps/agent_api/ source has no direct imports from the     concrete provid
- ConversationSession
- MagicMock
- bool
- str
- Retrieve loan from the database or raise 404.
- Retrieve loan from the database or raise 404.
- List all available tools.
- Convert a raw loan record into the LoanSummary response model.
- List all available tools.
- Retrieve basic details about a loan.
- Retrieve basic details about a loan.
- Return True when a case-insensitive borrower name match is found.
- Search loan records by borrower name and return up to 10 matches.
- List all available tools.
- Retrieve basic details about a loan.
- Search loans by borrower name (case-insensitive partial token match).
- Generate upcoming payment schedule.
- Generate upcoming payment schedule.
- Retrieve escrow account breakdown and disbursement history.
- Retrieve escrow account breakdown and disbursement history.
- Load the synthetic loans database from loans.json.
- Retrieve escrow account breakdown and disbursement history.
- Evaluate hardship program eligibility hints.
- Evaluate hardship program eligibility hints.
- Evaluate hardship program eligibility hints.
- Integrate with RAG providers to query policies.
- Integrate with RAG providers to query policies.
- Integrate with RAG providers to query policies.
- Integrate with RAG providers to query policies.
- Verify that the Bearer token matches the configured TOOLS_API_TOKEN.
- Verify escrow breakdown for loan 100245.
- Verify disaster forbearance checks for CA loan vs OH loan.
- Verify RAG-backed policy search endpoint.
- Verify that endpoints reject missing or invalid tokens.
- Verify listing tools works with valid token.
- Verify details can be retrieved for a valid loan ID.
- Verify 404 is returned for nonexistent loan ID.
- Verify schedule generation (matching example values for 100245).
- BaseModel
- ChatRequest
- allow
- ConversationSession
- Section A — Project Brief
- Section B — Agent System Prompt
- Section C — Build Prompt for AI Coding Agent
- Servicing Agent for Internal Care Reps — Prompt Bundle
- 11.1 Agent API (`apps/agent_api` — port 8000)
- 11.2 Tools API (`apps/tools_api` — port 8001)
- Product Requirements Document — Servicing Agent ("Helix")
- EligibilityHint
- EscrowBreakdown
- Average cost per turn in USD. Informational — no gate threshold.      Returns 0.
- Fraction of non-refusal/non-escalation items that have correct citations.      A
- Accuracy of refusal and escalation classification.      For each item:     - If
- Check metrics against thresholds, return list of breaches.      Args:         me
- EvalReport
- EvaluationResult
- Exception
- HealthResponse
- Eligibility
- Eligibility
- MagicMock
- object
- Any
- str
- Execute tool calls and return recorded items.
- Run a single agent turn and return structured output.
- Run a single agent turn and return structured output.
- Build the tool catalogue section from the available tools.      This is append
- Run a single agent turn and return structured output.      Args:         prom
- str
- ConversationSession
- int
- str
- Build history messages from a session using a sliding window strategy.
- str
- Raised when the LLM output cannot be parsed into ``AgentTurnOutput``.
- Try to extract a JSON object from the LLM response.      Handles cases where t
- str
- float
- str
- Return the configured vector store provider.
- Return the configured embedding provider.
- Return the configured content safety provider.
- Return the configured audit sink provider.
- Return the configured telemetry provider.
- Return the configured prompt store provider.
- Return a cached Settings instance â€” reads .env exactly once per process.
- str
- EvalItemResult
- float
- bool
- EvalItemResult
- float
- GoldenItem
- int
- str
- bool
- EvalItemResult
- float
- str
- GoldenItem
- float
- str
- int
- str
- packages/rag/
- int
- str
- str
- str
- Convenience wrapper for the safety middleware.     Obtains providers from facto
- PII anonymise inbound prompt. Write PII audit event.
- Content safety check outbound answer. Write safety audit event.
- str
- Replace detected PII spans with numbered tokens and provide reversal.      Examp
- Resolve tokens back to their original PII values.          Args:             tex
- Walk a dictionary and detokenize all string values.          This is used to res
- PaymentSchedule
- PennyMac Servicing Agent - Project Analysis
- 14.1 `ci.yml` — On every PR
- 14.2 `eval-gate.yml` — On PR + nightly
- 8.2 Outbound — Content Safety
- Servicing Agent — Architecture
- After each session
- Approval required before
- Build a step
- Check provider invariants
- Common workflows
- Knowledge graph (Graphify) — mandatory
- Module layout
- Provider Abstraction (load-bearing rule)
- Quick reference
- Read order
- Rules
- Rules (non-negotiable)
- Servicing Agent — AI Agent Instructions
- Tech stack
- What this project is
- When to use it
- After each session
- Approval required before
- Build a step
- Check provider invariants
- Common workflows
- Knowledge graph (Graphify) — mandatory
- Module layout
- Provider Abstraction (load-bearing rule)
- Quick reference
- Read order
- Rules
- Rules (non-negotiable)
- Tech stack
- What this project is
- When to use it
- Step 1.5 â€” Provider contracts (do before any feature work)
- Step 1 â€” Repo skeleton (acceptance: `make install lint test` exits 0)
- Step 2 â€” Synthetic data
- Step 3 â€” RAG pipeline
- Step 6 â€” Agent API
- PiiSpan
- PolicyChunks
- Reads SOPs from directory, chunks them, embeds them, and stores them in the vect
- SanitizeResult
- Settings
- Verify apps/agent_api/ source has no direct imports from the     concrete provid
- Patch all 10 provider factory functions with mock providers.      Also patches _
- A seeded regression must cause a threshold breach.      Simulates a scenario whe
- ThresholdBreach
- react
- react-dom
- redoc
- tailwindcss
- @tailwindcss/vite
- eslint
- @eslint/js
- eslint-plugin-react-hooks
- eslint-plugin-react-refresh
- globals
- @types/node
- @types/react
- @types/react-dom
- typescript
- typescript-eslint
- vite
- @vitejs/plugin-react
- build
- dev

## God Nodes (most connected - your core abstractions)
1. `r` - 118 edges
2. `o()` - 115 edges
3. `i` - 102 edges
4. `n` - 101 edges
5. `Lb` - 87 edges
6. `a()` - 83 edges
7. `l` - 65 edges
8. `p` - 63 edges
9. `u()` - 57 edges
10. `S` - 55 edges

## Surprising Connections (you probably didn't know these)
- `run_test()` --indirect_call--> `client()`  [INFERRED]
  scripts/probe_loan_api.py → apps/tools_api/tests/test_tools_api.py
- `LookupLoanRequest` --uses--> `Settings`  [INFERRED]
  apps/tools_api/main.py → packages/common/settings.py
- `GetPaymentScheduleRequest` --uses--> `Settings`  [INFERRED]
  apps/tools_api/main.py → packages/common/settings.py
- `GetEscrowBreakdownRequest` --uses--> `Settings`  [INFERRED]
  apps/tools_api/main.py → packages/common/settings.py
- `CheckHardshipEligibilityRequest` --uses--> `Settings`  [INFERRED]
  apps/tools_api/main.py → packages/common/settings.py

## Import Cycles
- None detected.

## Communities (496 total, 263 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.22
Nodes (15): str, packages/safety/, Convenience wrapper for the safety middleware.     Obtains providers from facto, SafetyPipeline, EvaluationResult, BaseModel, Result of inbound PII anonymization., Result of outbound content safety evaluation. (+7 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (54): date, MonkeyPatch, AbstractLoanDataProvider, _apply_delinquencies(), _as_dict_list(), _build_mock_escrow_breakdown(), _build_mock_payment_schedule(), _derive_delinquency_days() (+46 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (47): Agent runner — orchestrates a single agent turn.  Flow: 1. Load the system promp, AgentTurnOutput, Any, str, PromptStoreProvider, str, packages/agent_core/, Agent runner — orchestrates a single agent turn.  Flow: 1. Load the system pr (+39 more)

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (28): AISearchConfig, AOAIChatConfig, AOAIEmbeddingConfig, AuditConfig, BedrockChatConfig, BedrockEmbeddingConfig, ChatConfig, ConfluenceConfig (+20 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (120): Ad(), add(), Af, an(), At(), Bd(), bi(), Bn() (+112 more)

### Community 5 - "Community 5"
Cohesion: 0.20
Nodes (9): ProviderCallEvent, ProviderError, ProviderHealth, Exception, Shared provider base types for the Servicing Agent.  Project-specific helpers, Result of a single provider health check., Raised when a provider call fails after retries., Lightweight audit record for a provider invocation. (+1 more)

### Community 6 - "Community 6"
Cohesion: 0.12
Nodes (17): devDependencies, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @types/node, @types/react, typescript-eslint (+9 more)

### Community 7 - "Community 7"
Cohesion: 0.27
Nodes (10): lookup_loan(), LookupLoanRequest, Convert a raw loan record into the LoanSummary response model., Search loan records by borrower name., Retrieve basic details about a loan., Search loans by borrower name (case-insensitive partial token match)., search_borrower(), search_loans_by_borrower_name() (+2 more)

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (22): Any, int, str, Chunk, MarkdownChunker, Any, Markdown chunker for RAG pipeline., Split a large section into smaller chunks. (+14 more)

### Community 9 - "Community 9"
Cohesion: 0.11
Nodes (28): chat(), _get_bound_providers(), health(), lifespan(), Any, Servicing Agent API — FastAPI on :8000.  Endpoints:     POST /chat   — stream, Application lifespan: warm up providers on startup, flush audit sink on shutdown, Aggregate health of all 10 providers; 503 on any failure. (+20 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (48): EvalItemResult, float, Metric computation functions for the eval harness.  All functions are pure — the, Pydantic models for the eval harness data pipeline.  These models flow through:, Eval gate thresholds — do not lower without explicit approval.  These match Sect, AgentTurnOutput, Structured output from a single agent turn., compute_citation_coverage() (+40 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (41): GoldenItem, MockToolsClientProvider, Path, float, str, GoldenItem, Single golden Q&A item loaded from ``data/golden.jsonl``., _build_golden_file() (+33 more)

### Community 12 - "Community 12"
Cohesion: 0.09
Nodes (31): AbstractAuditSinkProvider, AbstractLLMProvider, AbstractPiiProvider, AbstractPromptStoreProvider, AbstractRerankerProvider, AbstractSecretsProvider, AbstractTelemetryProvider, AbstractToolsClientProvider (+23 more)

### Community 13 - "Community 13"
Cohesion: 0.14
Nodes (17): AgentTurnOutput, ChatProvider, LLMMessage, PromptStoreProvider, str, ToolsClientProvider, _execute_tools(), AgentTurnOutput (+9 more)

### Community 14 - "Community 14"
Cohesion: 0.13
Nodes (19): MockLLMProvider, MockPromptStoreProvider, MockToolsClientProvider, MockLLMProvider, MockPromptStoreProvider, MockToolsClientProvider, Tests for the system prompt loader., Loading a raw prompt (no fenced block) should return it as-is. (+11 more)

### Community 15 - "Community 15"
Cohesion: 0.14
Nodes (13): client(), Verify that endpoints reject missing or invalid tokens., Verify listing tools works with valid token., Verify details can be retrieved for a valid loan ID., Verify 404 is returned for nonexistent loan ID., Verify search borrower endpoint returns valid results., Verify 404 is returned for nonexistent borrower name., test_auth_required() (+5 more)

### Community 16 - "Community 16"
Cohesion: 0.09
Nodes (22): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection, moduleResolution (+14 more)

### Community 17 - "Community 17"
Cohesion: 0.25
Nodes (7): ChatProvider, Chat (LLM) provider protocol — re-exports from provider_contracts., provider(), ChatProvider, Contract tests for the chat (LLM) provider., Every ChatProvider implementation must pass these tests., TestChatProviderContract

### Community 18 - "Community 18"
Cohesion: 0.10
Nodes (20): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+12 more)

### Community 19 - "Community 19"
Cohesion: 0.07
Nodes (24): CitationItem, bool, EvalItemResult, float, str, EscalationItem, CitationItem, EscalationItem (+16 more)

### Community 20 - "Community 20"
Cohesion: 0.17
Nodes (13): AbstractEmbeddingProvider, AbstractVectorStoreProvider, Integrate with RAG providers to query policies., search_policy(), Path, str, get_embedding_provider(), get_vector_store_provider() (+5 more)

### Community 21 - "Community 21"
Cohesion: 0.12
Nodes (14): str, classify_intent(), Classify a rep prompt into an intent.      Returns a tuple of ``(intent_type,, Tests for the pure-function intent router., A normal servicing question should classify as ANSWER., Rate quote queries should be refused., Requests for financial advice should be refused., CFPB complaint mentions should escalate. (+6 more)

### Community 22 - "Community 22"
Cohesion: 0.14
Nodes (17): App(), AgentStepItem(), AgentSteps(), AgentStepsProps, BorrowerContextPane(), ChatMessage(), ChatMessageProps, ChatPane() (+9 more)

### Community 23 - "Community 23"
Cohesion: 0.06
Nodes (41): b, c(), d, dr(), E, ee(), f, Fr() (+33 more)

### Community 24 - "Community 24"
Cohesion: 0.13
Nodes (16): get_policy_source_provider(), Provider factory functions â€” the DI layer.  Each ``get_*_provider()`` reads fr, Return the configured policy source provider., AbstractPolicySourceProvider, ConfluencePolicyProvider, LocalFilePolicyProvider, PolicyPage, ABC (+8 more)

### Community 27 - "Community 27"
Cohesion: 0.19
Nodes (9): MockPromptStoreProvider, PromptStoreProvider, provider(), MockPromptStoreProvider, PromptStoreProvider, Contract tests for the prompt store provider., Every PromptStoreProvider implementation must pass these tests., TestPromptStoreProviderContract (+1 more)

### Community 28 - "Community 28"
Cohesion: 0.19
Nodes (9): MockToolsClientProvider, ToolsClientProvider, provider(), MockToolsClientProvider, ToolsClientProvider, Contract tests for the tools client provider., Every ToolsClientProvider implementation must pass these tests., TestToolsClientProviderContract (+1 more)

### Community 29 - "Community 29"
Cohesion: 0.23
Nodes (6): EmbeddingProvider, provider(), Contract tests for the embedding provider., Every EmbeddingProvider implementation must pass these tests., TestEmbeddingProviderContract, Embedding provider protocol — re-exports from provider_contracts.

### Community 30 - "Community 30"
Cohesion: 0.40
Nodes (9): int, str, _log(), main(), Validates all synthetic data artifacts for the Servicing Agent project.  Usage, Run all validations, print summary, return 0 on success., validate_golden(), validate_loans() (+1 more)

### Community 31 - "Community 31"
Cohesion: 0.20
Nodes (7): MockTelemetryProvider, provider(), Contract tests for the telemetry provider., Every TelemetryProvider implementation must pass these tests., TestTelemetryProviderContract, Telemetry provider protocol — re-exports from provider_contracts., TelemetryProvider

### Community 32 - "Community 32"
Cohesion: 0.23
Nodes (6): provider(), Contract tests for the vector store provider., Every VectorStoreProvider implementation must pass these tests., TestVectorStoreProviderContract, Vector store provider protocol — re-exports from provider_contracts., VectorStoreProvider

### Community 33 - "Community 33"
Cohesion: 0.26
Nodes (7): ContentSafetyProvider, Content safety provider protocol — re-exports from provider_contracts., provider(), ContentSafetyProvider, Contract tests for the content safety provider., Every ContentSafetyProvider implementation must pass these tests., TestContentSafetyProviderContract

### Community 34 - "Community 34"
Cohesion: 0.28
Nodes (7): AbstractContentSafetyProvider, get_content_safety_provider(), Return the configured content safety provider., Integration test for RuleBasedContentSafetyProvider.     Verifies that blocklis, Test that MockContentSafetyProvider returns a predictable result., test_mock_content_safety(), test_rule_based_content_safety()

### Community 35 - "Community 35"
Cohesion: 0.07
Nodes (26): 1. Settings, 2. Loan Data Provider, 3. Policy Source Provider, 4. .env Files, 5. Quick-Switch Convenience (PowerShell), Architecture: The Toggle, Automated, File Summary (+18 more)

### Community 36 - "Community 36"
Cohesion: 0.12
Nodes (27): async_get_loan_or_404(), check_hardship_eligibility(), CheckHardshipEligibilityRequest, get_escrow_breakdown(), get_loan_or_404(), get_payment_schedule(), GetEscrowBreakdownRequest, GetPaymentScheduleRequest (+19 more)

### Community 40 - "Community 40"
Cohesion: 0.21
Nodes (8): str, AbstractSessionStoreProvider, Protocol for conversation session storage., Create a new conversation session., Retrieve a session by ID, returning None if expired or not found., Append a new turn to an existing session., Delete a session entirely., Protocol

### Community 41 - "Community 41"
Cohesion: 0.12
Nodes (14): mock_chat_provider(), mock_prompt_store(), mock_tools_client(), MockLLMProvider, MockPromptStoreProvider, MockToolsClientProvider, Pytest configuration for agent_core tests., Return a MockPromptStoreProvider with a canned system prompt. (+6 more)

### Community 42 - "Community 42"
Cohesion: 0.07
Nodes (37): a(), assign(), block(), _blockNode(), break(), code(), const(), _def() (+29 more)

### Community 43 - "Community 43"
Cohesion: 0.12
Nodes (16): After each session, Approval required before, Build a step, Check provider invariants, Common workflows, Knowledge graph (Graphify) — mandatory, Module layout, Provider Abstraction (load-bearing rule) (+8 more)

### Community 44 - "Community 44"
Cohesion: 0.19
Nodes (7): MockSecretsProvider, provider(), Contract tests for the secrets provider., Every SecretsProvider implementation must pass these tests., TestSecretsProviderContract, Secrets provider protocol — re-exports from provider_contracts., SecretsProvider

### Community 49 - "Community 49"
Cohesion: 0.14
Nodes (13): dependencies, @slidev/cli, @slidev/theme-default, @slidev/theme-seriph, name, private, scripts, build (+5 more)

### Community 59 - "Community 59"
Cohesion: 0.08
Nodes (23): 10. PII patterns (Presidio), 11. Common one-liners, 12. Module layout (scaffold status), 13. Data directory, 14. Docker dependencies (local dev), 15. Commit conventions, 16. Web UI components (`apps/web_ui/`), 17. CI / CD (`.github/workflows/`) (+15 more)

### Community 61 - "Community 61"
Cohesion: 0.20
Nodes (9): [2026-05-28] — Step 7: Safety layer implemented, [2026-05-31] — Tooling: Graphify knowledge graph, [2026-06-08] — Fix mypy test monkeypatch signatures, [2026-06-09] — Fix Safety Middleware Showstopper, [2026-06-09] — Graphify-first rule added to all agent instructions, [2026-06-10] — Conversational Memory Feature, [2026-06-18] — Bedrock API Key Auth & PII Stub Fixes, [2026-06-18] — Fix EscrowBalance Field Collision (+1 more)

### Community 62 - "Community 62"
Cohesion: 0.33
Nodes (5): AI / agent context, Key constraints, Layout, Quick start, Servicing Agent for Internal Care Reps

### Community 63 - "Community 63"
Cohesion: 0.14
Nodes (14): Servicing Agent — Task Tracker, Step 10 — IaC + CI, Step 11 — Conversational Memory (Feature), Step 12 — Observability & Eval Dashboard, Step 1.5 — Provider contracts (do before any feature work), Step 1 — Repo skeleton (acceptance: `make install lint test` exits 0), Step 2 — Synthetic data, Step 3 — RAG pipeline (+6 more)

### Community 68 - "Community 68"
Cohesion: 0.15
Nodes (13): dependencies, lucide-react, react, react-dom, redoc, tailwindcss, @tailwindcss/vite, lucide-react (+5 more)

### Community 69 - "Community 69"
Cohesion: 0.07
Nodes (71): ac(), ae(), bc(), bo(), ca(), dc(), Di(), Do() (+63 more)

### Community 71 - "Community 71"
Cohesion: 0.14
Nodes (13): App.1 Golden Q&A seed (10 items), App.2 Agent output JSON schema, App.3 Tool function signatures and example responses, App.5 Open call-outs (please confirm before STEP 5), Appendix, `check_hardship_eligibility(loan_id: str, program: str) -> EligibilityHint`, `get_escrow_breakdown(loan_id: str) -> EscrowBreakdown`, `get_payment_schedule(loan_id: str, months: int = 3) -> PaymentSchedule` (+5 more)

### Community 72 - "Community 72"
Cohesion: 0.22
Nodes (15): LLMMessage, build_history_messages(), LLMMessage, Memory strategy — builds history context for the LLM., Build history messages from a session using a sliding window strategy.      St, Tests for the memory strategy., test_build_history_messages_budget(), test_build_history_messages_empty() (+7 more)

### Community 73 - "Community 73"
Cohesion: 0.26
Nodes (7): PiiProvider, provider(), PiiProvider, Contract tests for the PII provider., Every PiiProvider implementation must pass these tests., TestPiiProviderContract, PII provider protocol — re-exports from provider_contracts.

### Community 74 - "Community 74"
Cohesion: 0.50
Nodes (5): _make_mock_provider(), mock_all_factories(), Create a MagicMock that looks like a provider instance., Patch all 10 provider factory functions with mock providers.      Also patches, MagicMock

### Community 75 - "Community 75"
Cohesion: 0.08
Nodes (3): Ls(), Rs(), v

### Community 76 - "Community 76"
Cohesion: 0.19
Nodes (7): al(), de(), el(), fe(), fl(), ul(), yl()

### Community 77 - "Community 77"
Cohesion: 0.10
Nodes (3): bl(), ol(), rl()

### Community 78 - "Community 78"
Cohesion: 0.09
Nodes (28): be(), cn(), dn(), fn(), ge(), gl(), hl(), hn() (+20 more)

### Community 79 - "Community 79"
Cohesion: 0.22
Nodes (8): name, private, type, version, dependencies, name, private, scripts

### Community 80 - "Community 80"
Cohesion: 0.33
Nodes (6): scripts, build, dev, lint, postinstall, preview

### Community 82 - "Community 82"
Cohesion: 0.13
Nodes (15): ao(), As(), ci(), co(), Da(), fo(), lo(), ma() (+7 more)

### Community 83 - "Community 83"
Cohesion: 0.16
Nodes (17): DisbursementItem, EligibilityHint, LoanSummary, PaymentSchedule, PaymentScheduleItem, PolicyChunks, PolicyResultItem, BaseModel (+9 more)

### Community 84 - "Community 84"
Cohesion: 0.25
Nodes (7): Hybrid Architecture, Let's see it in action, LoanOps Agent, Strict Evaluation Gate, Thank You, The Problem, The Solution

### Community 85 - "Community 85"
Cohesion: 0.10
Nodes (22): aa(), Example(), fa(), hasType(), Header(), init(), initDiscriminator(), initOneOf() (+14 more)

### Community 86 - "Community 86"
Cohesion: 0.26
Nodes (11): _agent_owns_vector_store(), False when Qdrant runs in embedded path mode — Tools API owns the lock., BaseSettings, Settings, _get(), main(), _mask_token(), _preview_body() (+3 more)

### Community 88 - "Community 88"
Cohesion: 0.12
Nodes (16): 1. Identify Memory Strategy Effectiveness, 2. Find Conversations Where Memory Prevented Escalation, 3. Context Overlap & Redundancy, 4. Memory Impact on Tool Usage, Compliance Note, Conversation Memory Graph Models, Core Entities, Graph Schema Extensions for Graphify (+8 more)

### Community 89 - "Community 89"
Cohesion: 0.18
Nodes (15): _make_mock_session_store(), mock_session_store_factory(), Any, Tests for the chat memory endpoint., Test getting memory for a non-existent session., Create a mock session store provider., Patch the session store factory function., Test successful retrieval of chat memory. (+7 more)

### Community 90 - "Community 90"
Cohesion: 0.13
Nodes (14): 10. Escalation — Fraud, 1. Happy Path — Escrow Query, 2. Happy Path — Payment Schedule, 3. Happy Path — Escrow Status (simple), 4. Happy Path — Hardship Eligibility, 5. Refusal — Rate Quote (out of scope), 6. Refusal — Financial Advice (out of scope), 7. Escalation — CFPB Complaint (+6 more)

### Community 91 - "Community 91"
Cohesion: 0.10
Nodes (12): Ei(), gt(), i, ia(), ir(), Lt(), ri(), Rt() (+4 more)

### Community 93 - "Community 93"
Cohesion: 0.15
Nodes (12): Broken Components, Conclusion, Critical Issues, Design Excellence, Documentation Drift, Executive Summary, Fundamental Demo Limitations, LoanOps Agent Servicing Agent - Project Analysis (+4 more)

### Community 94 - "Community 94"
Cohesion: 0.18
Nodes (5): ay, dh(), Kv, qv, yb

### Community 95 - "Community 95"
Cohesion: 0.17
Nodes (5): il(), Iw, kl(), nl(), xl()

### Community 97 - "Community 97"
Cohesion: 0.17
Nodes (11): 1. Conversation Session Service, 2. Memory Context Provider, 3. Memory Strategy Interface, Architecture, Conversation Memory Extension Plan, Core Components, Current Architecture (Stateless), Extended Architecture (+3 more)

### Community 100 - "Community 100"
Cohesion: 0.18
Nodes (10): 15. RACI Matrix, 16. Risks & Mitigations, 18. Glossary, 1. Executive Summary, 2. Problem Statement, 3. Product Vision & Goals, Goals, Product Requirements Document â€” Servicing Agent ("Helix") (+2 more)

### Community 102 - "Community 102"
Cohesion: 0.10
Nodes (21): 10. Tools API, 11.1 Metrics & Thresholds, 11.2 CI Gate, 11. Eval Harness, 12.1 Local Dev (`make demo`), 12.2 Azure Production (target â€” IaC not yet implemented), 12. Deployment Topology, 13. Responsible AI Controls (+13 more)

### Community 106 - "Community 106"
Cohesion: 0.22
Nodes (9): 12.1 Grounding Rule, 12.2 Human-in-the-Loop (HITL), 12.3 PII Redaction at Ingress, 12.4 Content Safety at Egress, 12.5 Audit Trail, 12.6 Prompt-Injection Hardening, 12.7 Disclaimers, 12.8 Supervisor Oversight (+1 more)

### Community 107 - "Community 107"
Cohesion: 0.22
Nodes (9): 6. Functional Requirements, FR-1: Loan Data Lookup, FR-2: Policy Search & Citations, FR-3: Response Drafting, FR-4: Escalation Handling, FR-5: Refusal Handling, FR-6: PII Handling, FR-7: Rep UI (+1 more)

### Community 109 - "Community 109"
Cohesion: 0.60
Nodes (5): main(), print_props(), One-off: inspect swagger schemas for loan endpoints. Safe to delete., resolve_ref(), schema_ref()

### Community 111 - "Community 111"
Cohesion: 0.07
Nodes (10): activateOneOf(), constructor(), Ff, oh, pt(), sh, th, ui() (+2 more)

### Community 112 - "Community 112"
Cohesion: 0.25
Nodes (7): CFPB Complaints, Complaint Categories, Complaint Handling, Handling by Type, Notice of Error (NOE), Overview, Qualified Written Request (QWR)

### Community 113 - "Community 113"
Cohesion: 0.25
Nodes (7): Decision Outcomes, Evaluation Factors, Financial, Hardship, Hardship Evaluation Criteria, NPV Test, Property

### Community 114 - "Community 114"
Cohesion: 0.15
Nodes (9): ADR-001 â€” Orchestration: Microsoft Agent Framework, ADR-002 â€” Local LLM: Ollama + Llama 3.1 8B, ADR-003 â€” Rep UI: Streamlit, ADR-004 â€” Provider Abstraction Pattern, ADR-005 â€” Unified Agent Rules: AGENTS.md, ADR-006 â€” Rep UI: React with TypeScript, ADR-007 — Native Tool Calling, Servicing Agent â€” Architecture Decision Records (+1 more)

### Community 115 - "Community 115"
Cohesion: 0.09
Nodes (3): cl(), dl(), pl()

### Community 116 - "Community 116"
Cohesion: 0.29
Nodes (6): Examples from this repo, Scope rules, Step 1 — Show current status, Step 2 — Generate commit message, Subject rules, Types

### Community 117 - "Community 117"
Cohesion: 0.29
Nodes (6): Account Actions, Documentation Required for Investigation, Identity Theft and Fraud, Immediate Steps, Overview, Reporting

### Community 118 - "Community 118"
Cohesion: 0.29
Nodes (6): Annual Escrow Analysis, Cushion Limit, Overview, Shortage Handling, Surplus Handling, Timeline

### Community 119 - "Community 119"
Cohesion: 0.29
Nodes (6): Disaster Forbearance, Eligibility, FEMA Declaration Verification, Overview, Post-Forbearance Options, Terms

### Community 120 - "Community 120"
Cohesion: 0.29
Nodes (6): Documentation Required, Eligibility Criteria, Forbearance Program, Forbearance Terms, Overview, Qualifying Hardships

### Community 121 - "Community 121"
Cohesion: 0.29
Nodes (6): Military Service Members (SCRA), Military Spouse Protections, Overview, SCRA Foreclosure Protection, SCRA Interest Rate Cap, SCRA Requirements

### Community 122 - "Community 122"
Cohesion: 0.29
Nodes (6): Borrower Communication, Foreclosure Alternatives (Ordered by Preference), Foreclosure Prevention, Overview, State-Specific Protections, Timeline

### Community 123 - "Community 123"
Cohesion: 0.29
Nodes (6): Eligibility Criteria, Evaluation Factors, Loan Modification, Modification Types, Overview, Trial Period

### Community 124 - "Community 124"
Cohesion: 0.29
Nodes (6): Cash for Keys, Deed-in-Lieu of Foreclosure (DIL), Eligibility, Eligibility, Short Sale, Short Sale and Deed-in-Lieu

### Community 125 - "Community 125"
Cohesion: 0.29
Nodes (6): Accepted Payment Methods, ACH (Automated Clearing House), Check by Mail, Debit Card, Not Accepted, Wire Transfer

### Community 126 - "Community 126"
Cohesion: 0.29
Nodes (6): Late Payment Handling, Overview, Partial Payments, Payment Application Order, Payment Confirmation, Payment Processing

### Community 128 - "Community 128"
Cohesion: 0.21
Nodes (3): mv, Sv, Um

### Community 129 - "Community 129"
Cohesion: 0.33
Nodes (5): dest, destDir, here, root, src

### Community 130 - "Community 130"
Cohesion: 0.33
Nodes (5): Call Scoring, Dispute Resolution, Overview, QA Scoring Criteria, Quality Assurance and Call Monitoring

### Community 131 - "Community 131"
Cohesion: 0.33
Nodes (5): Common Dispute Reasons, Dispute Handling Steps, Escrow Dispute Resolution, Overview, Resolution Timelines

### Community 132 - "Community 132"
Cohesion: 0.33
Nodes (5): Can I remove escrow?, Common Borrower Questions, Escrow Q&A for Reps, When is my next analysis?, Why did my escrow payment go up?

### Community 133 - "Community 133"
Cohesion: 0.33
Nodes (5): CARES Act Protections, COVID-19 Forbearance, Key Policy, Overview, Repayment Options After COVID Forbearance

### Community 134 - "Community 134"
Cohesion: 0.33
Nodes (5): Default on Plan, Eligibility, Overview, Plan Terms, Repayment Plan

### Community 135 - "Community 135"
Cohesion: 0.33
Nodes (5): Application Steps, Incomplete Applications, Loss Mitigation Application Process, Overview, Required Documents

### Community 136 - "Community 136"
Cohesion: 0.33
Nodes (5): Documentation, Eligibility, Overview, Payment Deferral, Terms

### Community 137 - "Community 137"
Cohesion: 0.33
Nodes (5): Auto-Pay Enrollment, Cancellation, Disclosures Required, Enrollment Process, Overview

### Community 138 - "Community 138"
Cohesion: 0.33
Nodes (5): Federal Programs, Overview, Payment Assistance Programs, Rep Role, State Programs

### Community 139 - "Community 139"
Cohesion: 0.33
Nodes (5): Common Disputes, Escalation, Investigation Process, Overview, Payment Disputes

### Community 140 - "Community 140"
Cohesion: 0.33
Nodes (5): Application, Overview, Principal-Only Payments, Recasting, Rules

### Community 141 - "Community 141"
Cohesion: 0.33
Nodes (5): Consequences, Overview, Re-presentment Policy, Returned Payment Fee, Returned Payments (NSF)

### Community 142 - "Community 142"
Cohesion: 0.33
Nodes (5): Overview, Payoff Components, Payoff Information, What Reps Can Provide, What Reps Cannot Provide

### Community 143 - "Community 143"
Cohesion: 0.33
Nodes (5): California Foreclosure Laws, California Relief Programs, California-Specific Policies, Disaster Relief (CA), Homeowner Bill of Rights (HBOR)

### Community 144 - "Community 144"
Cohesion: 0.33
Nodes (5): Florida Foreclosure Laws, Florida Homestead Exemption, Florida Hurricane Relief, Florida Insurance, Florida-Specific Policies

### Community 145 - "Community 145"
Cohesion: 0.33
Nodes (5): New York Foreclosure Laws, New York Foreclosure Relief, New York Property Tax, New York-Specific Policies, New York Tenant Protection

### Community 146 - "Community 146"
Cohesion: 0.33
Nodes (5): Ohio Disaster Relief, Ohio Foreclosure Laws, Ohio Foreclosure Mediation, Ohio Property Tax, Ohio-Specific Policies

### Community 147 - "Community 147"
Cohesion: 0.33
Nodes (5): Texas Disaster Relief, Texas Foreclosure Laws, Texas Homestead, Texas Property Tax, Texas-Specific Policies

### Community 148 - "Community 148"
Cohesion: 0.33
Nodes (6): 7.1 Performance, 7.2 Security, 7.3 Reliability, 7.4 Maintainability, 7.5 Portability, 7. Non-Functional Requirements

### Community 149 - "Community 149"
Cohesion: 0.33
Nodes (5): Configuration, Graphify Setup, Installation, Output, Usage

### Community 150 - "Community 150"
Cohesion: 0.40
Nodes (4): Documentation, Escalation Procedure, Escalation Routing, When to Escalate

### Community 151 - "Community 151"
Cohesion: 0.40
Nodes (4): Disbursement Inquiry, Disbursement Schedule, Escrow Disbursements, Tax Disputes

### Community 152 - "Community 152"
Cohesion: 0.40
Nodes (4): Eligibility, Process, Risks to Borrower, Voluntary Escrow Removal

### Community 153 - "Community 153"
Cohesion: 0.40
Nodes (4): Available Programs, Escalation Criteria, Hardship Assistance Overview, Rep Role

### Community 154 - "Community 154"
Cohesion: 0.40
Nodes (4): Compelling Circumstances, Eligibility Criteria, Late Fee Waiver Policy, Waiver Process

### Community 155 - "Community 155"
Cohesion: 0.40
Nodes (4): How to Look Up Payment History, Information Available, Payment History Inquiry, What Not to Disclose

### Community 156 - "Community 156"
Cohesion: 0.40
Nodes (4): Payment Changes, Payment Schedule, Requesting a Payment Schedule, Standard Amortization

### Community 157 - "Community 157"
Cohesion: 0.40
Nodes (4): Escrow Balance at Payoff, Payoff Process, Payoff Processing Timeline, Requesting a Payoff Statement

### Community 158 - "Community 158"
Cohesion: 0.40
Nodes (5): 10.1 Synthetic Loans (`data/loans.json`), 10.2 Synthetic SOPs (`data/sops/`), 10.3 Golden Q&A Set (`data/golden.jsonl`), 10.4 RAG Pipeline, 10. Data Requirements

### Community 159 - "Community 159"
Cohesion: 0.40
Nodes (5): 11.1 Agent API (`apps/agent_api` â€” port 8000), 11.2 Tools API (`apps/tools_api` â€” port 8001), 11.3 Agent Output Schema (`AgentTurnOutput`), 11.4 Audit Record Schema, 11. API Contracts

### Community 160 - "Community 160"
Cohesion: 0.40
Nodes (5): 13.1 Metrics & Thresholds, 13.2 Eval Harness, 13.3 Sacred Rule, 13.4 CI Workflows, 13. Evaluation & Quality Gates

### Community 161 - "Community 161"
Cohesion: 0.67
Nodes (3): Verify that the Bearer token matches the configured TOOLS_API_TOKEN., verify_token(), HTTPAuthorizationCredentials

### Community 162 - "Community 162"
Cohesion: 0.40
Nodes (3): Expanding the ESLint configuration, React Compiler, React + TypeScript + Vite

### Community 163 - "Community 163"
Cohesion: 0.50
Nodes (4): 17.1 Hard Constraints, 17.2 Key Architecture Decisions (ADRs), 17.3 Assumptions, 17. Constraints & Assumptions

### Community 164 - "Community 164"
Cohesion: 0.50
Nodes (4): 4.1 Care Representative (Tier 1/2), 4.2 Supervisor, 4.3 Compliance Reviewer, 4. Users & Personas

### Community 165 - "Community 165"
Cohesion: 0.50
Nodes (4): 8.1 Module Layout, 8.2 Tech Stack, 8.3 Architecture Diagram, 8. System Architecture

### Community 166 - "Community 166"
Cohesion: 0.50
Nodes (4): 9.1 Provider Catalogue, 9.2 Pattern Rules, 9.3 CI Enforcement, 9. Provider Abstraction Pattern

### Community 167 - "Community 167"
Cohesion: 0.50
Nodes (4): 3.1 Provider Catalogue, 3.2 Pattern Rules, 3.3 Dependency Graph (what imports what), 3. Provider Abstraction Pattern

### Community 168 - "Community 168"
Cohesion: 0.67
Nodes (3): 5.1 In Scope (v1), 5.2 Out of Scope (v1), 5. Scope

### Community 169 - "Community 169"
Cohesion: 0.17
Nodes (12): A.10 Top risks and mitigations, A.1 Business problem, A.2 Users, A.3 In-scope and out-of-scope, A.4 Success metrics, A.5 Hybrid architecture, A.6.1 Provider Abstraction Pattern, A.6 Tech stack (+4 more)

### Community 172 - "Community 172"
Cohesion: 0.24
Nodes (10): get_chat_memory(), Retrieve the chat memory for a given session, showing which turns are active/ina, ChatMemoryResponse, ConversationSession, int, str, estimate_tokens(), export_memory_markdown() (+2 more)

### Community 173 - "Community 173"
Cohesion: 0.22
Nodes (10): AuditSinkProvider, ContentSafetyProvider, PiiProvider, evaluate_outbound(), AuditSinkProvider, ContentSafetyProvider, PiiProvider, PII tokenise inbound prompt. Write PII audit event.      Instead of destructiv (+2 more)

### Community 174 - "Community 174"
Cohesion: 0.67
Nodes (3): 14.1 `ci.yml` â€” On every PR, 14.2 `eval-gate.yml` â€” On PR + nightly, 14. CI / CD

### Community 175 - "Community 175"
Cohesion: 0.22
Nodes (4): df(), hi(), iy, Jv

### Community 181 - "Community 181"
Cohesion: 0.18
Nodes (24): _get_app(), _make_agent_output(), AgentTurnOutput, Any, Tests for the Agent API (apps/agent_api).  All provider dependencies are mocke, Import the app fresh (after patches are applied)., When all factories succeed, /health returns 200 with all providers ok., When one factory raises, /health returns 503. (+16 more)

### Community 189 - "Community 189"
Cohesion: 0.29
Nodes (5): bx, By, fw(), op(), sortOptions()

### Community 191 - "Community 191"
Cohesion: 0.19
Nodes (8): AuditSinkProvider, MockAuditSinkProvider, Audit sink provider protocol — re-exports from provider_contracts., provider(), AuditSinkProvider, Contract tests for the audit sink provider., Every AuditSinkProvider implementation must pass these tests., TestAuditSinkProviderContract

### Community 192 - "Community 192"
Cohesion: 0.29
Nodes (4): ig(), ng(), rg(), ug

### Community 193 - "Community 193"
Cohesion: 0.29
Nodes (6): Im, Nb(), nx(), Rb, tx(), Zv()

### Community 194 - "Community 194"
Cohesion: 0.26
Nodes (11): Session: 1af0e50b-fbd0-4d5e-ae9f-4c90748840c9, Session: 23820353-b84e-4ce8-b4e4-a0ecab9462d1, Session: sess-99, Turn 1 — user, Turn 2 — assistant, Turn 3 — user, Turn 4 — assistant, Turn 5 — user (+3 more)

### Community 195 - "Community 195"
Cohesion: 0.15
Nodes (3): hs(), Qw(), Xw()

### Community 197 - "Community 197"
Cohesion: 0.11
Nodes (20): Any, str, Text with no PII spans passes through unchanged., Detokenize reverses tokenize., detokenize_dict resolves tokens in tool call arguments., detokenize_dict handles nested dicts., Empty token map returns text unchanged., detokenize handles tokens without brackets (e.g. PERSON_1). (+12 more)

### Community 207 - "Community 207"
Cohesion: 0.26
Nodes (8): PiiSpan, Represents a redacted PII entity in text., Unit tests for PiiTokenizer., Multiple PERSON spans get distinct numbered tokens., Single PERSON span is replaced with [PERSON_1]., test_tokenize_multiple_same_type(), test_tokenize_single_person(), PII tokenizer — reversible token replacement for PII spans.

### Community 210 - "Community 210"
Cohesion: 0.25
Nodes (8): App.4.1 Base types (`packages/common/providers/base.py`), App.4.2 Example Protocol (`packages/common/providers/chat.py`), App.4.3 Settings (`packages/common/settings.py`) - excerpt, App.4.4 Factory (`packages/common/providers/factory.py`) - excerpt, App.4.5 Env-var binding table, App.4.6 Contract-test sketch (`packages/common/providers/contract_tests/test_chat.py`), App.4.7 CI gate (encodes "no concrete imports outside providers/"), App.4 Provider abstraction reference

### Community 219 - "Community 219"
Cohesion: 0.33
Nodes (5): cu(), Ou(), uu(), wu(), xu()

### Community 233 - "uy"
Cohesion: 0.33
Nodes (4): Iv(), nv(), Rv(), uy

### Community 234 - "Nm"
Cohesion: 0.60
Nodes (3): ev, Nm(), Ps()

### Community 236 - "14. Delivery Phasing & Milestones"
Cohesion: 0.67
Nodes (3): 14. Delivery Phasing & Milestones, Build Steps (POC Phase), Phase Overview

## Knowledge Gaps
- **657 isolated node(s):** `name`, `private`, `dev`, `build`, `lint` (+652 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **263 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_agent_turn()` connect `Community 13` to `Community 2`, `Community 9`, `Community 10`, `Community 14`, `Community 19`, `Community 21`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **Why does `AgentTurnOutput` connect `Community 10` to `Community 2`, `Community 11`, `Community 13`, `Community 14`, `Community 83`, `Community 19`, `Community 21`, `Community 181`?**
  _High betweenness centrality (0.007) - this node is a cross-community bridge._
- **Why does `i` connect `Community 91` to `Community 192`, `Community 4`, `Community 69`, `Community 201`, `Community 42`, `Nm`, `Community 76`, `uy`, `Community 78`, `Community 111`, `Community 75`, `Community 82`, `Community 85`, `Community 23`, `Community 189`?**
  _High betweenness centrality (0.007) - this node is a cross-community bridge._
- **Are the 87 inferred relationships involving `r` (e.g. with `a()` and `aa()`) actually correct?**
  _`r` has 87 INFERRED edges - model-reasoned connections that need verification._
- **Are the 37 inferred relationships involving `o()` (e.g. with `a()` and `code()`) actually correct?**
  _`o()` has 37 INFERRED edges - model-reasoned connections that need verification._
- **Are the 60 inferred relationships involving `i` (e.g. with `a()` and `ca()`) actually correct?**
  _`i` has 60 INFERRED edges - model-reasoned connections that need verification._
- **Are the 65 inferred relationships involving `n` (e.g. with `a()` and `aa()`) actually correct?**
  _`n` has 65 INFERRED edges - model-reasoned connections that need verification._