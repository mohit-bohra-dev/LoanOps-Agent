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
