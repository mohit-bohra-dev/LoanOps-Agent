# Servicing Agent â€” Architecture Decision Records

> Format: **Decision â†’ Context â†’ Alternatives â†’ Reasoning â†’ Status**

---

## ADR-001 â€” Orchestration: Microsoft Agent Framework

**Decision:** Use Microsoft Agent Framework as the primary orchestration framework.

**Context:** Need a Python-native orchestrator that integrates with Amazon Bedrock
and supports production-grade agents, tool use, workflows, telemetry, and AWS deployment.

**Alternatives:** Previous brief default, LangChain.

**Reasoning:** Microsoft Agent Framework is the successor path for Microsoft agent
development, combining agent abstractions, tool orchestration, workflows, telemetry,
and AWS integration while preserving a clean provider boundary in this repo.

**Status:** Superseded by ADR-031 — `agent-framework` was never imported;
orchestration now lives in `provider_contracts.agent_runtime`.

---

## ADR-002 â€” Local LLM: Ollama + Llama 3.1 8B

**Decision:** Use Ollama for local dev; no AOAI credentials required to run
`make demo`.

**Reasoning:** Zero-cost local dev, same code path as AWS via `ChatProvider`
Protocol.

**Status:** Accepted.

---

## ADR-003 â€” Rep UI: Streamlit

**Decision:** Streamlit for the internal rep UI.

**Reasoning:** Fastest path to a working two-pane layout for an internal tool.
Next.js is noted as a stretch in App.5.

**Status:** Superseded by ADR-006.

---

## ADR-004 â€” Provider Abstraction Pattern

**Decision:** All 10 external capabilities exposed as `typing.Protocol`
interfaces; concrete implementations selected at runtime from env vars.

**Reasoning:** Required for local-first / AWS-target hybrid without code forks.
See `docs/01-servicing-agent-prompts.md` Â§A.6.1 for full rationale.

**Status:** Accepted â€” load-bearing, do not modify without a new ADR.

---

## ADR-005 â€” Unified Agent Rules: AGENTS.md

**Decision:** Consolidate all AI coding-agent instruction files (`CLAUDE.md`,
`GEMINI.md`, `context.md`, and IDE-specific rule files) into a single
canonical `AGENTS.md` at the project root.

**Context:** The project had 6+ separate rule files across `.cursor/rules/`,
`.agents/rules/`, `.kiro/steering/`, `CLAUDE.md`, and `GEMINI.md`, all
containing overlapping subsets of the same constraints. This caused maintenance
drift and inconsistent enforcement across IDE contexts.

**Alternatives:** Keep per-IDE files in sync manually; use symlinks.

**Reasoning:** `AGENTS.md` is the 2025–2026 industry standard for cross-IDE
agent instructions, natively recognized by GitHub Copilot, Cursor, Windsurf,
Claude Code, Cline, and Gemini CLI. A single source of truth eliminates drift.
IDE-specific directories now contain thin pointers back to `AGENTS.md`.

**Status:** Accepted. Supersedes the `CLAUDE.md`-centric approach.

---

## ADR-006 â€” Rep UI: React with TypeScript

**Decision:** Migrate the internal rep UI from Streamlit to React with
TypeScript, using Vite as the build tool and Tailwind CSS v4 for styling.
Deploy to AWS Static Web Apps instead of AWS App Runner.

**Context:** Streamlit (ADR-003) was chosen for rapid prototyping during
the POC phase. As the project matures toward pilot, the UI needs richer
interactivity (SSE streaming, real-time tool traces, drag-and-drop panels),
type safety, and alignment with enterprise frontend patterns.

**Alternatives considered:**
- **Streamlit (status quo):** Limited interactivity, no component
  reusability, poor TypeScript story, vendor-specific deployment.
- **Next.js:** Server-side rendering and routing are unnecessary for a
  single-page internal tool behind auth — adds complexity without benefit.
- **Vue / Svelte:** Viable, but React has the largest ecosystem and most
  team familiarity.

**Reasoning:** React + TypeScript + Vite provides production-grade
interactivity, compile-time type safety, hot-module replacement, and
seamless integration with the existing FastAPI backend via Vite's proxy.
Tailwind CSS v4 (CSS-first `@theme`) eliminates config files and enables
a premium dark-mode design system.

**Status:** Accepted. Supersedes ADR-003.

---

## ADR-007 — Native Tool Calling

**Decision:** Migrate from JSON-based text tool parsing to native provider-level function calling (e.g., Ollama `tools`, OpenAI `tools`) across all `AbstractLLMProvider` implementations.

**Context:** The agent initially requested the LLM to output an `AgentTurnOutput` JSON object containing both the `answer` and `tool_calls` in a single generation pass. This caused two severe issues:
1. Smaller models (like Gemma 4) failed to reliably produce valid JSON with nested tool syntax, causing `AgentParseError`.
2. The agent was forced to "guess" the final answer before actually executing the tools, leading to hallucinations.

**Reasoning:** Native tool calling pushes the structured output constraint down to the provider API, eliminating parse errors. Splitting the agent loop into two passes (Pass 1: Tool generation -> Execute tools -> Pass 2: Final answer) allows the LLM to ground its draft reply in actual tool execution results.

**Status:** Accepted.

---

## ADR-008 — Live Confluence SOP ingest (composite, gitignored artifacts)

**Decision:** When `DATA__MODE=real`, policy source is a
`CompositePolicyProvider` of local dummy SOPs + `ConfluencePolicyProvider`.
Curated Escrow/Hardship pages are fetched via Confluence REST v2, converted
with Microsoft `markitdown`, PII-scrubbed (`regex` default), written to
`data/sops/_confluence/` (gitignored), and embedded into local Qdrant.

**Context:** Real Servicing Policies & Procedures (SC space) must feed RAG
without replacing the offline demo corpus and without committing confidential
internal docs.

**Alternatives:** Export-only markdown commit; query-time Confluence fetch;
`DATA__MODE=real` replacing local SOPs entirely.

**Reasoning:** Ingest-time live fetch matches existing provider scaffold;
composite preserves `make demo` offline; gitignored artifacts keep
confidential content out of git while remaining inspectable locally.

**New env vars:** `DATA__CONFLUENCE__PAGE_IDS`,
`DATA__CONFLUENCE__ANCESTOR_IDS`, `DATA__CONFLUENCE__EXPAND_CHILDREN`,
`DATA__CONFLUENCE__PII_SCRUB`, `DATA__CONFLUENCE__ARTIFACT_DIR`
(plus existing base_url/username/api_token/space_keys).

**Status:** Accepted.

---

## ADR-009 — Independent loan vs SOP source switches

**Decision:** Split `DATA__MODE` into:
- `DATA__LOAN_SOURCE` = `mock` | `real`
- `DATA__SOP_SOURCE` = `local` | `confluence` | `both`
- `DATA__SOP_CONFLUENCE_MODE` = `cache` | `live`

`DATA__MODE` remains as a deprecated backcompat alias
(`mock` → loan mock + sop local; `real` → loan real + sop both + live).

**Context:** Need mock loan fixtures with Confluence-only SOPs (no synthetic
local corpus), and the reverse combinations during integration.

**Alternatives:** Keep single `DATA__MODE`; add only a boolean
`DATA__USE_CONFLUENCE`.

**Reasoning:** Orthogonal axes match how demos actually run; cache mode
reuses `data/sops/_confluence/` offline without Confluence API credentials
at chat time.

**Status:** Accepted.

---

## ADR-010 — One modular Python product

**Decision:** LoanOps-Agent is the single product backend. Language is
**Python 3.11 only**. Shared vendor contracts live in `provider_contracts`
(imported editable, not copied). React `apps/web_ui` stays TypeScript (UI only).

Node SSE gateway and standalone plaisse-wiki are **sources to port, then retire**.
Modules: `packages/sse`, `packages/db`, `packages/docs`, `packages/wiki`, existing
`agent_core` / safety / eval. One FastAPI front door (`/chat`, MCP). Role or API
key allow-lists tools.

**Duplicates — keep one:**

| Job | Keep | Remove / do not port |
|-----|------|----------------------|
| Providers | `provider_contracts` | Grow local Protocols; wiki Titan/Redis stacks |
| Vector DB | pgvector via ABC | Qdrant at product runtime; wiki API-endpoint index |
| Call SSE API | `packages/sse` | Wiki `src/tools/api` |
| SQL | `packages/db` (one driver) | Second pool/driver |
| Orchestrator | `agent_core` | Gateway keyword chat; wiki LangGraph concierge |
| Chat UI | `apps/web_ui` | Gateway HTML/embed chat |
| HTTP | One FastAPI app (`agent_api`) | Gateway Express; **`apps/tools_api` removed** |
| Session | Postgres behind session-store ABC | Memory only as test double |
| Auth | API keys (agents) + Auth0 (humans) | Extra config files / tools-API bearer |

**Keep (not duplicates):** wiki doc-write, GitLab, Jira, commit watch, package/screen;
Helix SOP eval, PII middleware, approve/escalate.

**Embedding:** local `bge-small-en-v1.5`; AWS `amazon.titan-embed-text-v2:0` (1024-dim).
Reindex both corpora when model changes. Deploy reuses wiki AWS path (Python image).

**SQL prerequisite:** `aioodbc` + Microsoft ODBC Driver 18 for SQL Server.

**Status:** Accepted.

---

## ADR-011 — MCP server is a separate Streamable HTTP listener

**Decision:** Expose the four agent tools (`search_sse_apis`, `list_sse_apis`,
`call_sse_api`, `search_docs`) through a real Model Context Protocol server
using the official Python `mcp` SDK (FastMCP) and Streamable HTTP. The
listener binds `MCP__HOST` / `MCP__PORT` (default `127.0.0.1:8001`) at
`MCP__PATH` (default `/mcp`). It is a second process so it does not capture
the Agent API routes `/mcp/tools`, `/mcp/tools/call`, and `/mcp/keys`. Those
routes stay a custom JSON API. The chat agent keeps calling
`ModularToolsClient` in-process until a later client flag.

**Context:** ADR-010 keeps one FastAPI front door for chat. Remote MCP clients
(Cursor, Gemini) need the protocol, not that JSON wrapper. A mount of `/mcp`
on the Agent API would collide with `/mcp/tools`.

**Alternatives:** Hand-rolled JSON-RPC on the Agent API; stdio only; treat
`/mcp/tools` as MCP.

**Reasoning:** The SDK implements initialize, tools/list, and tools/call.
Execution stays in `ModularToolsClient` and `invoke_sse_api`. Auth is a
required bearer (`MCP__AUTH_TOKEN`); an empty token rejects every call.
`MCP__ROLE` selects the existing scope allow-list. `call_sse_api` on this
server is GET-only. Optional `x-loanops-user` and `x-loanops-tenant` are
audit fields only. Downstream SSE calls still use `SSE__API_KEY`.

**Settings:** `MCP__HOST`, `MCP__PORT`, `MCP__AUTH_TOKEN`, `MCP__ROLE`, `MCP__PATH`.

**Status:** Accepted.

---

## ADR-012 — SSE API knowledge graph is separate from LoanOps Graphify

**Decision:** Build a **SSE / enterprise API knowledge graph** from SSE application
**source code** (and OpenAPI / process metadata), for agent API discovery. Keep
**Graphify** scoped to the **LoanOps-Agent repository** only (developer code
graph). Do not store SSE operations, apps, or process edges in
`graphify-out/`.

**Context:** ADR-011 delivers MCP execution. Keyword `search_sse_apis` over an
OpenAPI catalog does not encode prerequisites or call order across many SSE
apps. Product direction follows the DeepLearning.AI / SAP pattern in
[Knowledge Graphs for AI Agent API Discovery](https://www.deeplearning.ai/courses/knowledge-graphs-for-ai-agent-api-discovery):
specs (and here also **source**) → graph → semantic retrieval → process edges →
small ordered API set → agent execute.

**Layer split:**

```text
LoanOps Graphify          → this repo's code/docs (dev aid only)
SSE API knowledge graph   → SSE apps, endpoints, process order (discovery)
Capability catalog        → callable MCP-facing capabilities (materialized from graph / OpenAPI)
MCP server                → execute capabilities via ModularToolsClient / invoke_sse_api
RAG (docs)                → policy text, not API selection
ARD (later)               → which MCP resource to connect to
```

**Alternatives:** Put SSE APIs into LoanOps Graphify; capability catalog only
with no graph; runtime graph walk instead of MCP.

**Reasoning:** Execution stays on MCP + existing HTTP clients. Discovery needs
relationships (process, prereqs) that a flat OpenAPI list lacks. Mixing SSE
enterprise nodes into LoanOps Graphify would poison both jobs. Offline graph
build from SSE **source** can enrich OpenAPI-only extraction; capability
records exposed to the agent should remain a bounded catalog, not the full
graph dump.

**Status:** Accepted. RDF implementation is ADR-014 (`packages/capability_kg`); not Graphify.

---

## ADR-013 — Agent tools via MCP client flag

**Decision:** Add `TOOLS_CLIENT__PROVIDER=mcp` so `run_agent_turn` /
`_execute_tools` call the Streamable HTTP MCP listener (`packages.mcp_server`)
instead of in-process `ModularToolsClient`. Default stays `modular`. Rollback is
setting the provider back to `modular`. The MCP server keeps using
`ModularToolsClient` / `invoke_sse_api` as the only SSE execution path.

**Context:** ADR-011 shipped the protocol server; chat still called tools
in-process. Architecture Phase 4 inserts the MCP hop for the agent only.
Sidebar custom `/mcp/tools` stays on the in-process client.

**Alternatives:** Always-on MCP with no flag; mount MCP on Agent API;
stdio-only client.

**Reasoning:** Factory flag preserves local-first `make demo` without a second
process. Same tool names and `ToolResult` shape. Client reuses `MCP__HOST` /
`MCP__PORT` / `MCP__PATH` / `MCP__AUTH_TOKEN`. Empty `MCP__AUTH_TOKEN` refuses
client construction. Align `AGENT_ROLE` with `MCP__ROLE` so scope allow-lists
match.

**Settings:** `TOOLS_CLIENT__PROVIDER` = `modular` | `mcp` (no new env keys
beyond the existing `MCP__*` listener block).

**Product shape (2026-10-02):** The servicing agent `/chat` path is a
**first-party MCP consumer**, not a parallel tools stack. Target runtime for
product demos and multi-client parity is `TOOLS_CLIENT__PROVIDER=mcp` against
the same Streamable HTTP endpoint Cursor/Gemini use. `modular` remains the
default for local-first `make demo` (single process) and as rollback — not as
a long-term alternate product architecture. Capability discovery for the agent
should flow through MCP tools (`search_sse_apis` / EAKG tools), not a second
in-process graph client beside MCP. **EAKG shards are the only enterprise
discovery source** (D4); ADR-014 single TTL is not used for product search.

**Status:** Accepted.

---

## ADR-014 — Capability knowledge graph uses RDFLib + SPARQL

**Decision:** Represent enterprise capabilities as an RDF graph using **RDFLib**,
persisted as Turtle for the prototype, queried with **SPARQL** behind a
`CapabilityCatalog` facade. Namespace is configurable
(`CAPABILITY_KG__NAMESPACE`). Do not use LoanOps Graphify, Neo4j, or NetworkX
as the capability registry. Do not dump the full graph to the LLM.

**Context:** ADR-012 separated SSE/enterprise discovery from Graphify. The
master architecture requires a semantic capability model (permissions, domains,
API mappings, review status) that keyword OpenAPI search cannot express.
MCP (ADR-011/013) already executes tools; discovery needs a capability layer.

**Alternatives:** Plain JSON graph; put capabilities in Graphify; one MCP tool
per OpenAPI operation; remote triple store only.

**Reasoning:** RDFLib keeps local-first `make demo` (file Turtle, no infra).
SPARQL supports exact constraints (readOnly, permission) while a later phase
adds semantic retrieval. Catalog API hides RDF from agent/MCP. ReviewStatus
enables human-in-the-loop without requiring manual creation of every capability.
Remote SPARQL store can replace the file later behind the same facade.

**Settings:** `CAPABILITY_KG__ENABLED`, `CAPABILITY_KG__NAMESPACE`,
`CAPABILITY_KG__APPROVED_ONLY`,
`CAPABILITY_KG__SEMANTIC` (Phase 9 cosine sidecar).

**Status:** Accepted.

**Amendment (2026-10-02 / D4):** **EAKG is the only product discovery source.**
`search_sse_apis` reads `data/eakg` shards only (no single-TTL fallback).

**Amendment (2026-10-20):** Removed `packages.capability_kg.build` and
`CAPABILITY_KG__TTL_PATH`. Shared `capability_kg` library remains for EAKG.

---

## ADR-015 — Enterprise ontology v2 with provenance

**Decision:** Extend the capability ontology (ADR-014) with Enterprise,
Repository, Deployable, ApiSurface, CodeUnit, DataStore, EventTopic,
SdkPackage, AuthProvider, CrossAppRelationship, Evidence, and Proposal
classes. Model cross-application edges as first-class nodes that must carry
at least one Evidence node (repositoryId, commitSha, filePath, line range,
detectorId, confidence). Structural facts come primarily from extractors;
LLM may **investigate** ledger gaps only under ADR-029 (candidates with
Evidence `detectorId=llm_investigate*`, review-gated; patterns via git).
Label/group overlays remain Proposal nodes (ADR-014 ReviewStatus).

**Context:** Pilot of Escrow, Fees, and LoanServices showed repeatable
platform idioms for cross-app calls, but relationships without provenance
cannot answer impact questions safely.

**Alternatives:** Bare predicate edges without Evidence; LLM-extracted graph;
Neo4j property graph from day one.

**Reasoning:** First-class relationship nodes keep confidence and review
status attachable. Evidence requirement matches the project citation rule.
LLM proposals stay human-gated (ADR-014 ReviewStatus). Gap-fill structural
writes are constrained by ADR-029 (investigator + pattern feedback, not
free-form GraphRAG).

**Status:** Accepted (plan approved 2026-10-02). **LLM boundary amended by
ADR-029** (2026-10-15, investigator architecture).

---

## ADR-016 — Repository Registry as onboarding entry point

**Decision:** All enterprise repositories are registered in
`data/eakg/registry/repositories.yaml` via `packages.eakg.registry`.
Repository IDs and GitLab project IDs are data, never hard-coded in
extractor or detector logic. Adding repository N requires a registry entry
plus optional technology extractor if the stack is new.

**Context:** Enterprise has 10+ apps; pilot starts with three. Architecture
must not be redesigned per repo.

**Alternatives:** Hard-code pilot repos; discover via GitLab group crawl only.

**Reasoning:** Explicit registry gives ownership, access status, index
status, and shard paths. GitLab group crawl can seed candidates later.

**Status:** Accepted (plan approved 2026-10-02).

---

## ADR-017 — Sharded RDFLib store for multi-repo EAKG

**Decision:** Persist one Turtle shard per repository under
`data/eakg/repos/<repositoryId>/` plus enterprise and cross_app graphs.
Merge via lazily loaded `ConjunctiveGraph` behind `CapabilityCatalog`.
Migrate to Neo4j/remote SPARQL only if merged triples exceed ~5M or p95
query latency exceeds 500 ms.

**Context:** Single in-process Turtle file does not scale past ~10–20 repos.
Full rebuild of all repos on one change is too expensive.

**Alternatives:** One monolith Turtle; Postgres graph tables; Neo4j now.

**Reasoning:** Shards preserve ADR-014 local-first and enable incremental
re-index. Facade hides the storage layout from MCP.

**Status:** Accepted (plan approved 2026-10-02). **Query/persist path
superseded by ADR-026** (HTTP SPARQL). Shard layout retained only as deprecated
local artifact until cutover completes.

---

## ADR-018 — Static .NET extraction: Roslyn primary, regex fallback

**Decision (amended 2026-10-15 multi-lang):** **Roslyn** syntax-tree extraction is
the primary .NET controller + Minimal API extractor (`tools/eakg-dotnet-extract`,
detector `dotnet_roslyn` v2.1.0). Selected via `EAKG__EXTRACTOR=auto|roslyn|regex`
(default `auto`: try Roslyn, fall back to regex). Packages, appsettings topics,
connection strings, proxies, and String.Format routes remain in the Python
regex module. **Tree-sitter** extracts structural HTTP routes for Python
(FastAPI/Flask) and Node/TypeScript (Express/Fastify) via detector ids
`treesitter_python` / `treesitter_node`. Onboard merges all API adapters by
canonical `METHOD:/normalized/path`. RDF operation/capability URIs hash that
route key (re-onboard required after upgrade). **CodeQL stays out** (license on
private clones; taint covered by SonarQube on SSE pipelines). Java/Go extractors
remain backlog. Primary extractors stay deterministic (Roslyn / regex /
tree-sitter). **LLM investigation of ledger gaps only under ADR-029**
(Evidence `detectorId=llm_investigate*`; default off; review before publish).

**Context:** Controllers use attribute routes and many attributes before the
method; regex window heuristics miss actions (e.g. GetLoanSummary). Stack board
chose Roslyn; `dotnet` SDK 8+ is available on the pilot workstation. Multi-stack
repos need the same `ApiOperationFact` shape without a proprietary SAST license.

**Alternatives:** tree-sitter-only; regex forever; full project compilation /
semantic model (heavier restores); CodeQL (license).

**Reasoning:** Syntax trees bind Http* attributes to the correct
MethodDeclaration without NuGet restore of app projects. Hybrid OpenAPI still
enriches when a token exists (`EAKG__OPENAPI_MODE`). Tree-sitter fills
non-.NET route surface with MIT wheels.

**Status:** Accepted; D5 Roslyn upgrade shipped 2026-10-02; multi-lang
tree-sitter + Minimal APIs shipped 2026-10-15. **LLM investigator amended
by ADR-029** (2026-10-15).

---

## ADR-019 — EAKG settings namespace and index schedule

**Decision:** All enterprise KG config uses `EAKG__*` nested settings
(`workspace_dir`, `registry_path`, `shard_dir`, `gitlab_host`,
`openapi_mode`, `live_spec_token`, `confidence_threshold`,
`auto_approve_structural`, `nightly_hour`, `review_stale_days`). Indexing
runs as three external triggers (per-merge `sync repo`, nightly
`sync nightly`, weekly `sync audit`) — no in-process scheduler daemon.

**Context:** AGENTS.md requires settings.py as the only env reader; clocks
belong to GitLab CI / Task Scheduler.

**Status:** Accepted (plan approved 2026-10-02).

---

## ADR-020 — uv workspace projects (csproj-style)

**Decision:** Split the monorepo into a uv workspace. Root `pyproject.toml`
is the solution (`[tool.uv.workspace] members = ["projects/*"]`). Each
`projects/LoanOps.X/pyproject.toml` is one project (`loanops-*`) with
third-party deps + `{ workspace = true }` project references. Import paths
stay `packages.*` / `apps.agent_api` via hatchling `force-include` and
implicit namespace packages (no `packages/__init__.py`).

**Composition layer:** `LoanOps.Tools` owns `ModularToolsClient`,
`McpToolsClient`, and tools-client factories so Common does not depend on
SSE/docs/db/wiki. EAKG capability search is injected into SSE search via
`capability_block` (breaks sse ↔ eakg ↔ capability_kg cycle).

**Enforcement:** `scripts/check_project_refs.py` fails if a non-test import
targets a package whose `loanops-*` dist is not declared (ProjectReference
gate). Wired into pytest + pre-commit.

**Status:** Accepted 2026-10-02.

---

## ADR-021 — Audience: general internal users (not care-rep-only)

**Decision:** Position LoanOps as an **internal AI platform for any authorized
enterprise role**. Capability discovery (EAKG), MCP tools, docs search, and
grounded drafts are the product. Care-rep workflows are one optional persona,
not the product definition.

**Context:** Team moved away from building care-rep-specific UX/flows; same
stack should serve engineers, PMs, ops, and others via role scopes.

**Alternatives:** Keep care-rep-only messaging; split a second product.

**Reasoning:** MCP + EAKG + scopes already support multi-role use. Docs and
`AGENT_ROLE=care_rep` naming were lagging the real direction.

**Implications:**
- Canonical role name `user` (same scopes as former default internal pack).
- `care_rep` kept as deprecated alias.
- One-pager: `docs/09-loanops-one-pager.md`. System prompt §B updated for
  internal colleague (not borrower).

**Status:** Accepted 2026-10-04.

---

## ADR-022 — Read-only tool policy and EAKG tools live in LoanOps.Tools

**Decision:** Enforce GET-only / no-body for `call_sse_api` in the execution
core (`packages/tools/policy.py` + `ModularToolsClient.call` + fail-closed
`invoke_sse_api`). MCP `execute_tool` keeps transport auth, role scope, capability
bind, and audit, and reuses the shared read-only asserts. EAKG discovery tools
(`search_capabilities`, `explain_capability`, `find_providers`, `impact_of_change`)
are implemented in `packages/tools/eakg_tools.py` and dispatched by
`ModularToolsClient`, not as private server helpers.

**Context:** Cursor → MCP (Flow C) is the primary client. Policy only at the MCP
door left modular/direct callers unprotected. EAKG logic in `server.py` made the
MCP process own business logic that belongs with the other tools.

**Alternatives:** Keep policy MCP-only; full `ToolRegistry` refactor in one pass.

**Reasoning:** Defense-in-depth without an auth redesign. Thin MCP wrappers stay
stable for Cursor `tools/list`. Full registry can follow later.

**Implications:**
- `ToolPolicyError` in Tools; MCP maps to `PolicyError`.
- `invoke_sse_api` rejects non-GET/HEAD and never sends a JSON body.
- Auth/identity/PII work remains deferred (see `docs/ARCHITECTURE_REVIEW_LAYER2.md` §8).

**Status:** Proposed 2026-04-08.

---

## ADR-023 — Cached EAKG catalog + OpenAPI embedding sidecar

**Decision:** Cache merged EAKG shards via `CapabilityCatalogService` (fingerprint
on shard file mtimes/sizes). Persist OpenAPI operation embeddings at
`<EAKG__SHARD_DIR>/enterprise/openapi_embeddings.json`. Semantic flag is
`CAPABILITY_KG__SEMANTIC` **or** sidecar present (same rule for search and bind).
Rebuild OpenAPI sidecar with
`uv run python -m packages.api_index.refresh all --sidecar-only`.
MCP `/health` is liveness; `/ready` reports catalog/EAKG/sidecar status.

**Context:** Cursor tool calls were re-merging RDF and optionally embedding every
OpenAPI op serially on cold start. Docs still described keyword-only search.

**Alternatives:** Process-global singleton without fingerprint; Qdrant for OpenAPI
vectors; keep in-memory-only embed cache.

**Reasoning:** Matches existing EAKG `embeddings.json` pattern. No new env vars.
Fingerprint invalidation is enough for local MCP demos.

**Implications:**
- Sidecar lives under gitignored `data/eakg/enterprise/`.
- Keyword fallback on embed failure is labeled in `search_sse_apis` output.
- Settings hot path uses `get_settings()` (`@lru_cache`).

**Status:** Proposed 2026-04-08. **Superseded as primary OpenAPI discovery** once
`API_INDEX__ENABLED=true` (ADR-024 vector index). Sidecar remains the labeled
fallback when the vector store is unavailable. Sidecar rebuild is
`packages.api_index.refresh` (`--sidecar-only`); the old `sse.embed_openapi`
wrapper CLI was removed.

---

## ADR-024 — Enterprise app scale: registry-driven API catalog (30+ apps)

**Decision:** The EAKG repository registry is the single source of truth for
which applications LoanOps can discover and call. Each registry entry carries
per-environment base URLs and an auth audience (seeded from TAAC
`ServiceUrls` / API `Identifier`). OpenAPI specs are fetched and cached by the
onboarding pipeline only; the MCP process builds its SSE catalog from cached
specs and makes no swagger requests at start-up. EAKG capabilities and OpenAPI
operations merge into one operation record keyed by
`application|METHOD|normalized_path`, embedded at index time and stored in the pgvector implementation of the
vector store provider (`VECTOR_STORE__PROVIDER=pgvector`, namespace per
environment). Qdrant stays a supported adapter, not the API-index default. Outbound credentials are
resolved per application through a new `CredentialBroker` provider protocol;
the concrete auth model (Auth0 M2M per destination, on-behalf-of, or static
token) stays pluggable and is not decided here. `SSE__SWAGGER_LINKS` /
`SSE__SWAGGER_URLS` remain as a local-development override only.

**Context:** Target is 30+ enterprise applications, not a POC. Today the app
list lives in two places (`repositories.yaml` with 3 apps, and
`SSE__SWAGGER_LINKS`), MCP fetches each swagger serially at first load, one
`SSE__API_KEY` is sent to every host, OpenAPI vectors live in a JSON sidecar
ranked by a Python loop, and EAKG ids (`GetLoanSummary`) differ from SSE catalog
ids (`loanservices:getLoanSummary`) so capability bind fails. Onboarding calls
`enrich_interface` without a `base_url`, so live spec fetch never runs there.
Smoke test 2026-10-08: discovery worked, all live GETs returned 401.

**Alternatives:**
- Keep adding links to `SSE__SWAGGER_LINKS` (serial boot fetch, one bearer,
  second app list — rejected).
- Qdrant for the API index (supported adapter, but the product index is
  pgvector, matching Plaisse wiki and the existing provider).
- Keep JSON sidecar (ADR-023) and Python ranking (fine below ~1k operations;
  no metadata filters, not shared across processes).
- Decide Auth0 M2M now (premature; auth program parked in
  `docs/ARCHITECTURE_REVIEW_LAYER2.md` §8).

**Reasoning:** Reuses existing parts (registry, TAAC ingest, `fetch_spec`,
shard OpenAPI cache, vector store + secrets providers). Moves all slow,
failure-prone work to the pipeline, isolates per-app failures, fixes the
capability/OpenAPI id split, and keeps local-first (`make demo` works with
fixtures, Qdrant in Docker, and a static-token broker).

**Implications:**
- Supersedes the OpenAPI sidecar part of ADR-023 as **primary** discovery when
  `API_INDEX__ENABLED=true`; the sidecar stays as the fallback when the vector
  store is unavailable.
- Settings / env: `EAKG__ENVIRONMENT`, `SSE__CATALOG_SOURCE`, `API_INDEX__*`,
  `CREDENTIALS__*` (G1–G10 approved 2026-10-09).
- New provider protocol `CredentialBroker` with static + mock + caching;
  `get_credential_broker()` is the 14th `get_*` in
  `packages/common/providers/factory.py`; contract tests required.
- Host allow-list is derived from the registry, not from swagger links.
- `/ready` reports per-app status (indexed, spec age, credential check).
- Delivery tracked in `.ai/specs/enterprise-app-scale/` (P1–P6 complete 2026-10-09).

**Status:** Accepted 2026-10-09. Implemented through Phase 6 (docs).

---

## ADR-025 — GraphRAG: do not add

**Decision:** Do not add GraphRAG (LLM entity/relation extraction, community
summaries, graph-aware doc retrieval). Policy answers stay flat vector RAG
(`search_docs`). Graph questions about apps and capabilities stay on EAKG.
Full write-up: `docs/GRAPHRAG_REVIEW.md`.

**Context:** Asked whether GraphRAG should be added on top of docs RAG, EAKG,
and the ApiIndex pgvector store. SOP corpus measured 2026-10-09: 60 markdown
files, ~339 KB. Golden set ~50 items, no global-summary questions.

**Alternatives:**
- GraphRAG now — rejected. Community summaries have no `policy:` source, so
  they fail the citation rule and citation-coverage 1.0. Local 8B extraction
  is non-deterministic (eval moves between index runs). Corpus is an order of
  magnitude too small. A graph store would be a new Provider Protocol.
- Wire the existing reranker into `DocsService.search` — preferred next step.
  `get_reranker_provider()` already exists and is unused by docs search.
- Hybrid keyword + vector plus path/front-matter metadata — same shape as
  ApiIndex, no LLM.
- Deterministic doc-link file (markdown links, SOP → capability id), one-hop
  expand, each neighbour still a citable chunk.

**Reasoning:** EAKG already answers cross-app and impact questions. GraphRAG's
remaining value is multi-hop over a large interlinked doc corpus, which this
repo does not have. Citations require source text, not generated summaries.

**Revisit when any two hold:** corpus past ~2,000 docs or ~20k chunks; 20+
global/multi-policy golden items still fail faithfulness ≥ 0.85 after the
three alternatives ship; source becomes dense narrative (runbooks,
postmortems); summaries can cite back to source chunks with a pinned
extraction model.

**Clarification (2026-10-15, ADR-029):** ADR-025 still bans **GraphRAG**
(LLM entity/relation extraction over the SOP/doc corpus for retrieval).
It does **not** ban **EAKG investigation**: after rule extractors run, an
optional LLM may propose **candidates** (and pattern rules) for ledger gaps
under ADR-029. That path is EAKG indexing, not doc GraphRAG.

**Status:** Deferred 2026-10-09. Recommendation recorded. Not a build.
GraphRAG ban unchanged; EAKG LLM investigator is ADR-029.

---

## ADR-026 — EAKG runtime store is HTTP SPARQL (GraphDB local, Neptune later)

**Decision:** Product EAKG **query and persist** go through a **`GraphStoreProvider`**
over SPARQL 1.1 HTTP. Local operator store is **Ontotext GraphDB Free** (disk-backed,
data directory outside this git repo, Workbench for visualization). AWS target is
**Neptune RDF** (same client, different `GRAPH_STORE__*` URLs). RDFLib may build
triples during extract only; it is **not** the runtime query store. No in-process
merged `Graph` on the MCP request path. No Turtle shards under `data/eakg/` as
product truth.

**Supersedes (partial):** ADR-017 “query = lazily merged Turtle shards.” Shard files
remain deprecated ingest artifacts only until cutover; onboard **uploads named
graphs** to the SPARQL endpoint instead of writing `graph.ttl` / `evidence.ttl`.
ADR-017’s scale trigger (~5M triples / p95 > 500 ms) still applies for capacity
planning; the remote store is SPARQL (Neptune RDF), not Neo4j.

**Context:** Enterprise path needs disk-backed SPARQL (cloud-like), visualization,
no Docker, and no graph files in this repository. In-memory RDFLib merge does not
meet those constraints.

**Env (via `settings.py` only):**

| Var | Role |
|-----|------|
| `GRAPH_STORE__QUERY_URL` | SPARQL query endpoint (default `http://localhost:7200/repositories/loanops`) |
| `GRAPH_STORE__UPDATE_URL` | SPARQL update endpoint (default `…/repositories/loanops/statements`) |
| `GRAPH_STORE__AUTH_TOKEN` | Optional Bearer (empty for local GraphDB; Neptune later) |
| `GRAPH_STORE__TIMEOUT_SECONDS` | HTTP timeout (default 30) |

Named graph IRI per repo: `{CAPABILITY_KG__NAMESPACE}namedGraph/{repositoryId}`.

**Operator setup (local):** Install GraphDB Free (Windows). Create repository
`loanops`. Data dir outside the LoanOps-Agent clone. Workbench:
`http://localhost:7200`. Load via `python -m packages.eakg graph-load` (or onboard
upload). CI uses a fake HTTP SPARQL double — GraphDB not required in CI.

**Alternatives:** RDFLib shards (rejected for runtime); Fuseki/Oxigraph via Docker
(no Docker); Blazegraph (unmaintained); Neo4j property graph (forces query rewrite;
Neptune RDF keeps SPARQL).

**Reasoning:** One Provider Protocol, GraphDB Workbench for viz now, Neptune later
with env swap only. Fail closed if the endpoint is unreachable (no silent
`data/eakg` fallback).

**Status:** Accepted 2026-10-09 (plan approved).

---

## ADR-027 — EAKG non-graph artifacts in Postgres

**Decision:** Persist registry, `interface.json`, OpenAPI cache (+ pointer),
repo manifests, and ApiIndex `operations.json` in **Postgres** via an
`EakgArtifactStore` Protocol. Default product backend is Postgres (same
`loanops` DB as pgvector). `file` backend remains for unit tests / offline CI.
RDF graphs stay in GraphDB (ADR-026) — not duplicated into Postgres.

**Context:** After ADR-026, Turtle is no longer product truth, but registry and
join inputs still lived under `data/eakg/`. Enterprise path needs a queryable
catalog without repo-local JSON blobs.

**Env (via `settings.py` only):**

| Var | Role |
|-----|------|
| `EAKG_STORE__BACKEND` | `postgres` (product) \| `file` (tests) |
| `EAKG_STORE__DSN` | asyncpg DSN; empty → derive from `VECTOR_STORE__PGVECTOR_DSN` |
| `EAKG_STORE__FILE_SHARD_DIR` | File-backend root (default `data/pipeline_store`) |

**Tables:** `eakg_registry`, `eakg_interface`, `eakg_openapi`, `eakg_manifest`,
`eakg_operations`, plus `eakg_capability_embeddings`, `eakg_proposals`,
`eakg_decisions`, `eakg_engineering`, `eakg_graphrag`, `eakg_kv`, `sop_page_cache`.

**Amendment (2026-10-20):** Product path is DB-only — GraphDB + Postgres +
pgvector. **No S3.** File backend mirrors those stores under
`data/pipeline_store/{GraphDb,Postgres,Pgvector}` for tests/offline. Legacy
`data/eakg/repos|enterprise|…` is not product layout. SOP product ingest is
live Confluence → pgvector `docs` (optional file-mode cache under
`Postgres/sop_page_cache`).

**Alternatives:** Keep YAML/JSON files (rejected for product); S3-only blobs
(rejected — no transactional registry, extra ops surface); stuff RDF into
Postgres (rejected — SPARQL stays GraphDB).

**Reasoning:** One DB for vectors + catalog metadata; GraphDB for graph query;
file backend keeps `make test` / CI without Postgres and mirrors folder names
to the real stores.

**Status:** Accepted 2026-10-12; amended 2026-10-20 (DB-only + mirrored file layout).

---

## ADR-028 — Business process knowledge graph (pilot)

**Decision:** Represent Confluence SOP business processes as RDF in the existing
EAKG SPARQL store (ADR-026), using a **deterministic rule-based extractor**
as the primary path. An LLM may draft curated gazetteer / phrase-map YAML
**offline** (humans approve maps in git). **Additionally**, under ADR-029,
process ledger items (`partial`/`stub`) may be investigated only after the
fixture benchmark passes; candidates use Documentation provenance and
`detectorId=llm_investigate_process*`. Core `extract_page` stays LLM-free.
Pilot scope: Account Maintenance hub + three leaf SOPs. All process nodes
load as `pending_review`. Process graph data **never** authorizes or denies
API calls.

**Context:** External review of the process-KG plan required source-completeness
tracking, path-level graph validation, capability-link lifecycle, document
provenance (not code `Evidence`), and a clear LLM boundary vs ADR-025.

**LLM boundary:**
- Suggestions in `data/process_kg/maps/*.yaml` are not facts until versioned,
  reviewed, and approved.
- Each extraction records `extractorVersion` + `mapsHash`. Map changes mark
  dependent processes `reextract_required`.
- Runtime investigation (ADR-029) is opt-in (`EAKG__INVESTIGATE_AGENT`);
  publishes only after review; still not GraphRAG over the full SOP corpus.

**Five status dimensions** (separate predicates; do not overload `hasReviewStatus`):
- `sourceCompleteness`: `lossy_unverified` | `verified_complete` | `complete_unverified`
- `extractionStatus`: `full` | `partial` | `stub`
- `validationStatus`: `pass` | `fail`
- `hasReviewStatus`: existing lifecycle + `needs_reapproval`
- `sourceStatus`: `current` | `stale`

**Provenance:** Reuse `Documentation` (page id, URL, version, content hash).
Steps/transitions carry `sourceSection` + `sourceOrdinal`. Do **not** reuse
code-oriented `Evidence`. Graph stores short step labels only — no SOP quotes.

**Ontology (new):** `BusinessProcess`, `ProcessStep`, `Transition`,
`CapabilityLink`, `BusinessSystem`, `Regulation`. SOP roles are literals
(`sopRoleLabel`), never `Role` resources.

**Non-goals:** MCP process-query tool; capability-search ranking; process data
as authorization input; crawling ~30 remaining sibling pages until pilot metrics.

**Status:** Accepted 2026-10-15 (plan approved; pilot loads stay `pending_review`).
**Runtime LLM investigation for partial extracts amended by ADR-029**
(2026-10-15; gated on fixture benchmark).

---

## ADR-029 — Deterministic extract, LLM investigation, pattern feedback

**Decision:** Deterministic analyzers establish EAKG facts and own coverage.
An optional LLM **investigator** (flag `EAKG__INVESTIGATE_AGENT`, default
**off**) may only work items from a deterministic **gap ledger**. Everything
it produces is a **candidate** (`pending_review`, `callable=false`) that must
pass a validation gate and human review before publish.

When three or more ledger items share a **shape key**, the agent may propose
a **pattern** (YAML under `data/eakg/patterns/`) or an **extractor-change**
request (TASKS.md). Patterns require a backtest (motivating recall, zero
regression on established facts, unrequested-match report) and a human git
merge. Approved patterns load into deterministic extractors on the next run
(`patterns_hash`; change → `reextract_required`). Patterns only widen
detection — never capability semantics, authz, or callable status.

**Coverage cannot be delegated to the LLM.** `select_analyzers` output is a
persisted coverage manifest; incomplete runs are reported as incomplete.
Conflicts between analyzers become `ConflictRecord`s (deterministic), not
LLM reconciliations. Implementation facts (Roslyn / tree-sitter / Graphify)
must not be promoted into governed capability relationships by the agent.

**Amends:** ADR-015 (candidates + Evidence/`llm_investigate*`, not silent
structural writes); ADR-018 (rules remain primary; LLM investigates gaps);
ADR-028 (process investigator only after fixture benchmark passes).
**Does not amend** ADR-025’s GraphRAG ban for policy/doc retrieval.

**Context:** Design review rejected LLM-primary / agent-driven coverage.
Restricting writes to sinks does not guarantee correctness or completeness.

**Alternatives:** LLM-primary extract (rejected); tool-calling agent owning
extractor selection (rejected — coverage hole); proposals-only labels forever
(insufficient for OpenAPI/cross-app holes).

**Reasoning:** Rules establish facts; agent investigates ambiguity and
proposes patterns so the pipeline needs the model less over time.

**Implementation:** `coverage`, `gap_ledger`, `candidate_gate`,
`investigate_agent`, `patterns`, `pattern_backtest`; CLI
`investigate` / `patterns backtest`.

**Status:** Accepted 2026-10-15 (revised from gap-fill / LLM-primary after
design review). Flag default off.

---

## ADR-031 — Agent runtime via provider_contracts (LangGraph)

**Decision:** Orchestration engines live in `provider_contracts.agent_runtime`
(`LangGraphAgentRuntimeProvider`, `NativeLoopAgentRuntimeProvider`,
`MockAgentRuntimeProvider`). `LoanOps.AgentCore` selects via
`AGENT_RUNTIME__PROVIDER` and `get_agent_runtime_provider()`. Domain policy
(prompts, tool schemas, citation/schema validator) stays in LoanOps.

**Context:** ADR-001 listed Microsoft Agent Framework, but the package was
unused; `_agent.py` used a hand-rolled loop. Need swappable engines that still
expose parallel tool fan-out, validator retry, streaming events, and
in-memory checkpoint/resume without leaking framework types into domain code.

**Alternatives:** Keep manual loop; adopt Microsoft Agent Framework; bind
LangGraph only inside LoanOps.AgentCore (rejected — breaks provider lockstep).

**Reasoning:** Same pattern as LLM/vector_store — swap engines with `.env`;
CI boundary keeps SDKs in `provider_contracts`.

**Status:** Accepted. Supersedes ADR-001.


## ADR-032 — EvalStore via Langfuse for Layers 7-9

**Decision:** Langfuse is the eval system of record for L7 robustness, L8
operations, and L9 governance, accessed only through a new
`EvalStore` provider in `provider_contracts` (ABC + `langfuse` +
`jsonl` + `mock`). LoanOps.Common exposes `get_eval_store_provider()`.
Default provider is `jsonl` so CI and local demos need zero Langfuse
credentials. Telemetry and eval scores are separated by Langfuse
`environment` (`prod` vs `eval` / `local`).

**Context:** Layers 1-5 are deterministic/canned runners. L7 needs N-repeat
pass-rates, L8 needs prod MCP trace SLOs separate from offline scores, L9
needs dataset approval, rubric versions, and adjudication. Langfuse is
already the `langfuse` extra, backs `TelemetryProvider`, and receives
MCP `mcp.tool.call` spans. Sacred `packages/eval/thresholds.py` must
not change; L7 pass-rates and L8 SLOs live in new files.

**Alternatives:** Promptfoo for L7 + Langfuse for L8/L9; DeepEval/Confident;
Inspect AI; Braintrust; LangSmith datasets.

**Reasoning:** One system covers datasets, experiment runs, scores, score
configs (rubrics), annotation queues, and environments. Provider lockstep
keeps the SDK out of domain packages. JSONL default preserves local-first.

**New env vars:** `EVAL_STORE__PROVIDER` (`jsonl`|`langfuse`, default
`jsonl`), `EVAL_STORE__JSONL_DIR` (default `./out/eval_store`),
`TELEMETRY__LANGFUSE__ENVIRONMENT` (default `local`).

**Status:** Accepted 2026-10-29 (plan implementation).


## ADR-033 — Pipeline control plane: FastAPI + Postgres ledger; Step Functions on AWS

**Decision:** Knowledge pipelines are managed by a LoanOps-owned control plane:
FastAPI `/pipelines/*` routes + a Postgres (or file) run ledger
(`eakg_pipeline_runs`) + an Eval Portal Pipelines tab. Local PoC launches
`python -m packages.pipelines execute <run_id>` via `subprocess.Popen`.
On AWS, the same entrypoint runs under Step Functions → ECS `RunTask`
(existing Fargate sync task). Dagster stays an optional later engine for
asset lineage / cascade — not required for Phase 1.

**Context:** Seven knowledge pipelines already exist as Python callables
(EAKG, ApiIndex, embeddings, docs, GraphRAG, Engineering KG). Ops today
is CLI / optional in-process scheduler / EventBridge→ECS for EAKG only.
Assessment rejected n8n, Airflow/MWAA, Kestra, Glue, and Bedrock Knowledge
Bases as the primary orchestrator: they add UI/infra without replacing the
need for LoanOps-specific catalog, hash freshness, and eval linkage.

**Alternatives:** Dagster as primary; Amazon MWAA; Step Functions alone
(no LoanOps UI/ledger); keep CLI-only.

**Reasoning:** One entrypoint keeps local `make demo` (zero AWS) and AWS
Fargate identical. Ledger lives next to existing ADR-027 artifacts.
Step Functions only wraps ECS for multi-step / scheduled AWS runs.
Provider lockstep (`PipelineOrchestratorProvider`) deferred until AWS
engine lands (new env var needs approval).

**Status:** Accepted 2026-11-10 (Phase 1 PoC).
