# Decide (D) and Cleanup (C) board

Simple tracker for the post-EAKG-pilot cleanup.  
**D** = decisions (pick a path). **C** = hygiene (do the work).

Related: [`TASKS.md`](../TASKS.md), [`PHASE_STATUS.md`](PHASE_STATUS.md), [`EAKG_COMMITTED_VS_LOCAL.md`](EAKG_COMMITTED_VS_LOCAL.md), [`MCP_CLIENT_INTEGRATION.md`](MCP_CLIENT_INTEGRATION.md), [`STACK_LAYER_DECISIONS.md`](STACK_LAYER_DECISIONS.md).

Last updated: **2026-10-02**.

---

## What is “D”?

**Decide** items. Product/architecture forks. One choice so the team does not chase two north stars.

## What is “C”?

**Cleanup** items. Housekeeping after the pilot (clutter, stale docs, backlog sorting). Not new features.

---

## Scoreboard

| Bucket | Count |
|---|---|
| **D done / locked** | D1–D8, D10; D9 deferred |
| **D still open** | — (none) |
| **C done** | C1–C6 (all) |

---

## D — Decisions

| ID | Name | Layman meaning | Choice / status |
|---|---|---|---|
| **D1** | Primary path | What do we build toward? | **Locked: A+B+C = MCP platform.** EAKG fills tools; agent `/chat` + Cursor/Gemini all consume same `:8001/mcp`. Not “chat with its own tools stack.” See ADR-013. |
| **D2** | Graph search on by default? | Should capability search use the knowledge graph without flipping a switch? | **Done — `true`.** Default `CAPABILITY_KG__ENABLED=true`. Turn off anytime: `CAPABILITY_KG__ENABLED=false` in `.env`. |
| **D3** | Approved-only filter? | Show only human-approved edges, or everything we discovered? | **Done — `false`.** Show full discovered graph. Later: `CAPABILITY_KG__APPROVED_ONLY=true` when review process is owned. |
| **D4** | One map or two? | Keep old single-file graph **and** new multi-repo EAKG, or EAKG only? | **Done — EAKG only.** Product search reads `data/eakg` shards. Single-TTL fallback **removed**; seed `capabilities.ttl` deleted; `CAPABILITY_KG__TTL_PATH` deprecated (build CLI only). |
| **D5** | How we read .NET code | Roslyn vs regex vs tree-sitter for controller extract | **Done — Roslyn shipping.** `EAKG__EXTRACTOR=auto` (default): Roslyn tool then regex fallback. Force `roslyn` / `regex`. Tool: `tools/eakg-dotnet-extract`. [`STACK_LAYER_DECISIONS.md`](STACK_LAYER_DECISIONS.md) |
| **D6** | Fourth app repo? | Onboard another Plaisse app beyond Escrow/Fees/LoanServices? | **Done — freeze at 3.** Escrow / Fees / LoanServices enough for now. Repo #4+ later via [`EAKG_ONBOARD_REPO.md`](EAKG_ONBOARD_REPO.md) when ready |
| **D7** | User identity into APIs | Real on-behalf-of (OBO) vs pass headers + shared service key? | **Done — simplest = Subservicing M2M.** Put Auth0 **M2M** Bearer (SubservicingClient `Auth0M2M` / `IJwtRetriever`, audience `https://pennymac`) into `SSE__API_KEY`. One service token covers all Plaisse APIs that trust that audience. Still process-wide (not per-rep). Keep `x-loanops-user` / `x-loanops-tenant` for audit. **No** login, per-API user tokens, token exchange, or RBAC this phase. Later: auto-fetch M2M → user OBO → RBAC. |
| **D8** | How to approve edges | Web UI or CLI? | **Done — both.** CLI now (`python -m packages.eakg review --pilot`); Web UI also in scope (same review model / decision log). Ship UI when product needs it; CLI stays. |
| **D9** | Push branch? | Publish local `vdd` commits to GitLab? | **Deferred — not yet.** Test everything first; push when green. |
| **D10** | Auto re-index? | Nightly/merge CI + Windows Task Scheduler, or manual sync? | **Done — manual only.** Run sync/CLI by hand when needed. **No** Windows Task Scheduler, **no** live GitLab CI schedules. Scripts + docs stay as reference; cloud/scheduler only after you choose later. |

### D1 options (plain English)

| Option | One sentence |
|---|---|
| **A** | Grow the enterprise knowledge graph (apps, edges, schedule). |
| **B** | Agent `/chat` calls tools **through MCP** (same server as IDEs). |
| **C** | Prove Cursor and Gemini on that same MCP endpoint (evidence tables). |

**Together:** graph fills MCP → agent + IDEs consume MCP.

### D4 context (why it mattered)

| Map | What it was | Fate |
|---|---|---|
| Old small map | One `capabilities.ttl` from a Loan Services OpenAPI fixture | **Deleted from discovery** |
| New big map (EAKG) | Per-app shards + cross-app edges (Escrow/Fees/LoanServices) | **Source of truth** |

No shards on disk → search falls back to OpenAPI keywords only (not the old TTL).

---

## C — Cleanup

| ID | Name | Layman meaning | Status |
|---|---|---|---|
| **C1** | Graphify backups | Dated `graphify-out/20YY-…` folders clutter git status | **Done** — removed; `.gitignore` has `graphify-out/20*/` |
| **C2** | Keep secrets/shards local | Live clones and Turtle shards must not be committed | **Done** — only `registry/` + `fixtures/` in git |
| **C3** | Fix TASKS focus line | “Current focus” must match real north star | **Done** — MCP consumer + EAKG feeds tools |
| **C4** | Fix phase tracker | Stop pointing “next” at finished Phase 9 | **Done** — MCP platform north star (2026-10-02) |
| **C5** | Committed vs local doc | One page: what is in git vs machine-only | **Done** — [`EAKG_COMMITTED_VS_LOCAL.md`](EAKG_COMMITTED_VS_LOCAL.md) |
| **C6** | Sort backlog | Open work into Now / Next / Later | **Done** — top of [`TASKS.md`](../TASKS.md) |

---

## Suggested next

1. **Now** bucket: MCP evidence (Cursor/Gemini); `SSE__API_KEY` = Subservicing Auth0 **M2M** token (covers all APIs). Re-index via **manual** EAKG CLI when needed.  
2. **D9** after full local test pass — then push `vdd`.  
3. Schedulers (Task Scheduler / GitLab CI) stay off until you opt in later.  
4. Later: auto-fetch M2M → user OBO → RBAC (only when product needs it).

Update this file whenever a **D** is decided (Status + one-line note).
