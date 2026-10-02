# Phase 1 Plan

**Goal:** Close the enterprise capability discovery → MCP → execute loop **without rewriting** working Roslyn / RDF / MCP / SSE pieces.  
**Stop after this plan for review** — no Phase-1 implementation until approved.

Related: [`ARCHITECTURE.md`](../ARCHITECTURE.md), [`TARGET_ARCHITECTURE.md`](TARGET_ARCHITECTURE.md), [`PHASE_STATUS.md`](PHASE_STATUS.md), [`DECIDE_AND_CLEANUP.md`](DECIDE_AND_CLEANUP.md).

---

## 1. Phase-1 intent

Ship a **capability-first, policy-enforced** path on top of existing code:

```text
Evidence-backed EAKG → (optional approved-only) Catalog
  → MCP search → bound operation → invoke_sse_api
```

Phase 1 is **hardening + bind + govern**, not “build MCP/RDF/Roslyn again.”

---

## 2. In / out of scope

### In scope

| # | Work item | Why |
|---|---|---|
| P1.1 | Document + freeze target diagrams in-repo (this pack) | Shared north star |
| P1.2 | **Capability-bound invoke contract** | Search returns capability → execute only mapped `operation_id` / method / path; reject unbound / mismatched calls |
| P1.3 | Enforce **`requiresPermission`** at MCP edge | Metadata already in RDF; unused today (`MCP_SECURITY.md`) |
| P1.4 | Align **readOnly** with GET-only policy | Prefer capability `readOnly` + HTTP method; fail closed |
| P1.5 | Governance toggle path | Runbook for `CAPABILITY_KG__APPROVED_ONLY=true` + `review`/`publish`; keep CLI (D8) |
| P1.6 | Provenance visible in `explain_capability` | Evidence in client-facing explain output (already partial — fill gaps) |
| P1.7 | Golden / smoke for capability → MCP → GET | Eval or scripted smoke; **do not lower** thresholds |
| P1.8 | Restore or replace deleted `CURRENT_ARCHITECTURE.md` pointer | Point readers to Assessment + living `ARCHITECTURE.md` / `FLOWS.md` |

### Explicitly out of scope (Phase 1)

| Item | Reason |
|---|---|
| Rebuild FastMCP / Streamable HTTP | Done (ADR-011) |
| Rebuild RDFLib catalog / ontology v1 | Done (ADR-014/015) |
| Replace Roslyn with something else | Done primary (D5) |
| CodeQL | Later |
| Tree-sitter | Later |
| ARD integration | Later (Phase 14) |
| Full OBO / Auth0 user token exchange | D7 deferred |
| Review Web UI | D8 later; CLI sufficient for Phase 1 |
| Graphify → RDF enrichment | Phase 10 |
| One MCP tool per OpenAPI op | Anti-pattern |
| Repo #4+ onboard | D6 freeze at 3 |
| Gemini validation | Track separately (Phase 12); not blocked by P1.2–P1.4 |
| Schedulers / live CI re-index | D10 manual only |

---

## 3. Mapping user’s “implementation order” → reality

| User step | Status entering Phase 1 | Phase-1 action |
|---|---|---|
| 1. Inspect architecture | Done (Assessment) | Review docs only |
| 2. Roslyn + OpenAPI evidence | **Done** | No rewrite; fix only binding bugs if found |
| 3. RDF Capability Catalog | **Done** (EAKG) | Consume; do not fork second catalog |
| 4. Semantic + SPARQL retrieval | **Done** (optional flag) | Keep; document when to enable |
| 5. MCP Streamable HTTP | **Done** | Harden policy only |
| 6. Cursor → MCP → Capability → API | **Partial** (Cursor ✓; bind weak) | **P1.2–P1.4** |
| 7. Governance / permissions / provenance / eval | **Partial** | **P1.3–P1.7** |
| 8. CodeQL / multi-language | Later | Out |
| 9. ARD | Later | Out |

---

## 4. Proposed work packages (after approval)

### WP-A — Capability bind at execute (highest leverage)

**Problem:** Discovery can return capabilities; `call_sse_api` still accepts free-form `operation_id` / method / path the model invents.

**Approach (sketch — implement only after review):**

1. Prefer execute args that include `capability_id` **or** require prior search hit cache / explicit allow from catalog lookup.
2. Server resolves capability → `operation_id` + method + path template from RDF.
3. Reject if client-supplied method/path disagree with catalog.
4. Keep tool name `call_sse_api` (or thin alias) to avoid client churn.

**Do not:** reimplement HTTP client; do not add per-op tools.

**Touch (expected):** `packages/mcp_server/policy.py` + `server.py`, possibly thin helper in `packages/eakg` / `capability_kg`; tests in `packages/mcp_server/tests`.

### WP-B — Permission + readOnly enforcement

1. Load `requiresPermission` for resolved capability.
2. Map MCP role / principal → allowed permissions (start: static map from `scopes.py` / settings — **no LLM**).
3. If permission missing → `PolicyError` before invoke.
4. If `readOnly=false` → reject on current read-only MCP server (writes stay off Phase 1).

**Touch:** `policy.py`, settings if new allow-list needed (**ADR if new env vars**).

### WP-C — Governance runbook + optional approved-only demo path

1. Document: `review --pilot` → `publish` → set `CAPABILITY_KG__APPROVED_ONLY=true`.
2. Smoke: EAKG tools read only `approved.ttl`.
3. Do **not** flip default to true globally until owners agree (respect D3).

### WP-D — Evaluation / smoke

1. Scripted: `search_capabilities` → bound GET → HTTP 200 on known synthetic/live op (e.g. getLoanSummary) via MCP.
2. Negative: wrong method, disallowed permission, unknown host → reject.
3. Optional golden subset with `TOOLS_CLIENT__PROVIDER=mcp` when Bedrock SSO green — thresholds unchanged.

### WP-E — Docs hygiene

1. Add stub or redirect at `docs/CURRENT_ARCHITECTURE.md` → Assessment + `ARCHITECTURE.md` (file currently deleted).
2. Cross-link TARGET + PHASE_1 from `PHASE_STATUS.md` / `TASKS.md` (checkbox only after implement).

---

## 5. Acceptance criteria (Phase 1 done)

- [ ] Cursor (and LoanOps MCP client) can discover a capability and invoke **only** its mapped GET operation through existing SSE client.
- [ ] MCP rejects: non-GET / body / host outside allow-list / missing scope / missing `requiresPermission` (when configured).
- [ ] Evidence / review status visible via explain (or equivalent) for at least one pilot capability.
- [ ] No new dependency on ARD, CodeQL, or tree-sitter.
- [ ] Graphify still unused at runtime and unused as capability store.
- [ ] Working Roslyn extractor, EAKG shard merge, FastMCP server, and `invoke_sse_api` **unchanged in role** (only policy/bind wrappers added).
- [ ] Eval thresholds not lowered; smoke/tests green for policy rejects + one happy path.
- [ ] ADRs updated only if new env vars or authz model change (approval required).

---

## 6. Suggested sequencing (post-approval)

```text
WP-E docs pointer (cheap)
  → WP-A capability bind
  → WP-B requiresPermission + readOnly
  → WP-C governance runbook / approved-only demo
  → WP-D smoke + optional MCP golden
  → stop; Phase 2 backlog = CodeQL / UI review / OBO / ARD / Gemini evidence
```

---

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Bind too strict breaks current Cursor demos | Feature-flag bind enforcement; ship warn-then-enforce |
| Permission map incomplete | Start deny-unknown when enforcement on; document map |
| Scope creep into OBO | Keep D7 M2M; principal headers audit-only |
| Rewriting “cleaner” MCP | Reject in review — extend `packages/mcp_server` |

---

## 8. Decision needed from reviewers

1. **Approve Phase-1 WPs A–E** as written?  
2. **Bind enforcement:** hard-fail vs flag-gated first?  
3. **`APPROVED_ONLY`:** keep default false (D3) or demo-true for pilot?  
4. Restore `CURRENT_ARCHITECTURE.md` as redirect-only, or leave deleted?

**No implementation until these are answered.**
