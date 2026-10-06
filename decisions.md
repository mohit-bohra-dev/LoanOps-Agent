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

**Status:** Accepted â€” this overrides the original orchestration default in
`docs/01-servicing-agent-prompts.md`.

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
`CAPABILITY_KG__TTL_PATH`, `CAPABILITY_KG__APPROVED_ONLY`,
`CAPABILITY_KG__SEMANTIC` (Phase 9 cosine sidecar).

**Status:** Accepted.

**Amendment (2026-10-02 / D4):** **EAKG is the only product discovery source.**
`search_sse_apis` reads `data/eakg` shards only (no single-TTL fallback).
`CAPABILITY_KG__TTL_PATH` / `packages.capability_kg.build` remain for offline
experiments; they do not feed agent/MCP search.

---

## ADR-015 — Enterprise ontology v2 with provenance

**Decision:** Extend the capability ontology (ADR-014) with Enterprise,
Repository, Deployable, ApiSurface, CodeUnit, DataStore, EventTopic,
SdkPackage, AuthProvider, CrossAppRelationship, Evidence, and Proposal
classes. Model cross-application edges as first-class nodes that must carry
at least one Evidence node (repositoryId, commitSha, filePath, line range,
detectorId, confidence). Structural facts come from extractors; LLM writes
only Proposal overlays.

**Context:** Pilot of Escrow, Fees, and LoanServices showed repeatable
platform idioms for cross-app calls, but relationships without provenance
cannot answer impact questions safely.

**Alternatives:** Bare predicate edges without Evidence; LLM-extracted graph;
Neo4j property graph from day one.

**Reasoning:** First-class relationship nodes keep confidence and review
status attachable. Evidence requirement matches the project citation rule.
LLM proposals stay human-gated (ADR-014 ReviewStatus).

**Status:** Accepted (plan approved 2026-10-02).

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

**Status:** Accepted (plan approved 2026-10-02).

---

## ADR-018 — Static .NET extraction: Roslyn primary, regex fallback

**Decision (amended 2026-10-02 D5 upgrade):** **Roslyn** syntax-tree extraction is
the primary controller/operation extractor (`tools/eakg-dotnet-extract`, detector
`dotnet_roslyn`). Selected via `EAKG__EXTRACTOR=auto|roslyn|regex` (default
`auto`: try Roslyn, fall back to regex). Packages, appsettings topics,
connection strings, proxies, and String.Format routes remain in the Python
regex module. Tree-sitter and CodeQL are **Phase 2**. No LLM in structural
extraction.

**Context:** Controllers use attribute routes and many attributes before the
method; regex window heuristics miss actions (e.g. GetLoanSummary). Stack board
chose Roslyn; `dotnet` SDK 8+ is available on the pilot workstation.

**Alternatives:** tree-sitter-only; regex forever; full project compilation /
semantic model (heavier restores).

**Reasoning:** Syntax trees bind Http* attributes to the correct
MethodDeclaration without NuGet restore of app projects. Hybrid OpenAPI still
enriches when a token exists (`EAKG__OPENAPI_MODE`).

**Status:** Accepted; D5 Roslyn upgrade shipped 2026-10-02.

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

