# Enterprise AI Evaluation Platform — Architecture Assessment

**Status:** Evidence-based analysis only (no code changes).  
**Date:** 2026-11-03  
**Primary references:** [Hamel Husain — Your AI Product Needs Evals](https://hamel.dev/blog/posts/evals/) (2024-03-29); [ombharatiya/ai-system-design-guide — AI Evals study guide](https://github.com/ombharatiya/ai-system-design-guide/blob/main/ai_evals_comprehensive_study_guide.md); repo `docs/eval/LAYERS.md`, `packages/eval/**`, `provider_contracts/eval_store/**`, ADR-032.  
**Legend (status):** Implemented | Partial | Missing | Needs improvement | Not relevant  

Claims cite paths. Items not verified from the repo are marked **ASSUMPTION** or **RECOMMENDATION**.

---

## 0. Hamel (2024) — three levels vs LoanOps

Hamel’s core claim: products plateau when teams only change prompts (#3) without **eval + debug + change** as a flywheel. Domain-specific evals beat generic benchmarks. Keep tooling simple; remove friction from looking at data; Level 1 before heavy Level 2 judges; binary good/bad labels first; track human↔judge correlation (precision/recall, not raw agreement when imbalanced).

| Hamel level | Meaning | LoanOps today | Gap |
|---|---|---|---|
| **L1 Unit tests** | Fast, cheap assertions on features/scenarios; run on every change; track over time | Nine-layer deterministic scorers (MCP L1, tool select/args/traj/outcome, robustness canned) ≈ Hamel L1 | CI history/dashboards thin; `cost_usd` stub; no Metabase-style trend UI |
| **L2 Human & model eval** | Log traces; humans look at lots of data; domain-specific viewer; then LLM critique aligned to humans | MCP traces + Langfuse/EvalStore; L9 kappa/calibrate/promote; Ragas | **AgentCore untraced**; no domain review UI (chat-only); no habitual “look at all fails” workflow; judge alignment spreadsheet/`judgy` missing |
| **L3 A/B testing** | Live outcome experiments after product maturity | Not in repo | Correctly deferred until offline+review loop works |
| **RAG sub-evals** | Evaluate retrieval separately (points to Jason Liu) | Answer-level Ragas + ApiIndex top-5 recall; no unified retrieval harness | Matches our Phase 1 retrieval gap |
| **Superpowers** | Eval infra → fine-tune data + debugging | Promote candidates + golden JSONL; debug overlap intended | Fine-tune not a near-term goal; debugging blocked by agent trace gap |

**Hamel vs our nine layers:** Orthogonal. Hamel = *cadence/cost stack* (assert → human/judge → A/B). LoanOps layers = *failure surface* (MCP → tools → path → answer → safety → robustness → ops → governance). Keep both: run LoanOps L1–L5/L7 as Hamel Level 1 in CI; use LoanOps L8/L9 + humans as Hamel Level 2.

**Hamel maxims that should reorder Phase 1 slightly:**

1. **Remove friction from looking at data** > building more metrics — AgentCore traces + Langfuse deep-links beat a thick portal.
2. **Look at traces before more LLM judges** — error analysis before expanding Ragas/custom judges.
3. **Binary pass/fail labels first** — thumbs + reason codes match Hamel; skip fancy Likert early.
4. **Don’t buy generic eval frameworks** — reinforces ADR-032 (no Phoenix/Promptfoo as SoR).
5. **Track tests over time outside CI** — archive `out/eval-*.json` / EvalStore runs; simple dashboard later.

---

## Executive verdict

LoanOps already has a **strong nine-layer offline MCP/agent eval skeleton** (L1–L5 deterministic + L7–L9 via EvalStore/Langfuse). That is ahead of many internal agent platforms.

What is **not** yet an Enterprise AI Evaluation & Improvement Platform:

1. **No product UI** for review, feedback, failure triage, or golden promotion (`apps/web_ui` is chat-only).
2. **No dedicated Layer 6** hard-fail suite and no unified **retrieval eval** across EAKG / ApiIndex / SOP / GraphRAG / Graphify.
3. **Incomplete observability loop**: MCP spans exist; **AgentCore does not call `TelemetryProvider`** — full agent trajectories are not first-class traces.
4. **Governance CLIs exist** (kappa, promote-to-candidates) but lack human workflow UX, judge TPR/TNR calibration (`judgy`), and production failure → golden closed loop.
5. Guide chapters on **error analysis / axial coding**, **multi-turn**, and **improvement lifecycle** are largely **missing** as operable product capabilities.

**Do not** replace the nine-layer model or add Promptfoo/DeepEval/Phoenix as a second system of record. **Extend** ADR-032 Langfuse + EvalStore + deterministic scorers. Prefer Langfuse UI + thin LoanOps portal glue over a new database.

---

## 1. Current Architecture Assessment

### 1.1 What we already have (verified)

| Capability | Evidence |
|---|---|
| Nine-layer taxonomy (portal-aligned) | `docs/eval/LAYERS.md` |
| L1 MCP: protocol / contracts / functional / errors / perf | `packages/eval/mcp/` — `make eval-mcp-l1` |
| L2 tool selection (alternatives, forbidden, known MCP set) | `packages/eval/selection/score.py` |
| L3 argument scoring | `packages/eval/arguments/` |
| L4 constraint trajectories (not exact sequence) | `packages/eval/trajectory/` |
| L5 deterministic grounding + citations + optional Ragas | `packages/eval/outcomes/`; `packages/eval/run.py` + `thresholds.py` |
| L7 N-repeat / variants / FaultyToolsClient / Wilson LB | `packages/eval/robustness/` |
| L8 ops SLOs + sampled prod scoring (fixture + live-store) | `packages/eval/operations/`; `data/eval/ops_slos.yaml` |
| L9 registry, rubrics, validate/sync/agreement/calibrate/promote | `packages/eval/governance/`; `data/eval/registry.jsonl` |
| EvalStore provider lockstep (jsonl default, langfuse optional) | ADR-032; `provider_contracts/eval_store/`; `get_eval_store_provider()` |
| MCP tool telemetry (`mcp.tool.call`, latency, outcome) | `packages/mcp_server/server.py` |
| Safety middleware (PII inbound, outbound evaluate) | `packages/safety/` |
| MCP GET-only + role scopes | `packages/mcp_server/policy.py`, `scopes.py` |
| Knowledge pipelines (EAKG, ApiIndex, Docs, GraphRAG, Graphify) | packages under `projects/LoanOps.*` |
| ApiIndex top-5 recall regression (scale suite) | `api_index/tests/test_scale.py::test_top5_recall` |
| Capability embedding rank smoke tests | `capability_kg/tests/test_capability_kg.py` |
| EAKG human review CLI (catalog publish) | `packages/eakg/review.py` — **knowledge** review, not agent eval |

### 1.2 What works well

- **Layered decomposition** matches the guide’s “code-based first, LLM judge when needed” principle (Ch. 5 + Ch. 4).
- **Constraint-based L2/L4** correctly avoids brittle exact-tool-sequence grading (guide Ch. 7 state-level idea, adapted).
- **Sacred thresholds** (`thresholds.py`) + separate L7/L8 threshold files honor non-regression discipline (guide Ch. 11).
- **Provider abstraction** for EvalStore/Telemetry prevents SDK sprawl and keeps local-first (`jsonl`).
- **MCP L1 split suites** align with portal rules (protocol error ≠ tool `isError`).

### 1.3 Limitations and architectural gaps

| Gap | Severity | Evidence |
|---|---|---|
| No Evaluation Portal / review UI | High | `apps/web_ui/src/*` — ChatMessage has citations/steps, **no** feedback controls |
| Layer 6 dedicated suite absent | High | `LAYERS.md` “Partial”; no `packages/eval` safety/injection package; no `make eval-l6` |
| Agent path not traced via TelemetryProvider | High | Grep `AgentCore` → zero TelemetryProvider/span usage |
| Agent tool surface ≠ MCP surface | High | Agent `_SSE_ANSWER_TOOLS` = 4 tools; MCP registers 10 (`docs/eval/analysis.md` still accurate here) |
| Unified retrieval eval missing | High | No Recall@K/MRR harness spanning Docs/EAKG/GraphRAG/Graphify; only ApiIndex scale recall + unit ranking |
| Error analysis / failure taxonomy / clustering | High | No axial-coding pipeline; no failure category store tied to traces |
| Multi-turn / multi-session eval | Medium | No multi-turn golden or scorer in `LoanOps.Eval` |
| LLM-judge productization | Medium | Ragas in `run.py`; L9 `calibrate` = kappa only; no TPR/TNR/`judgy` |
| AuthZ eval suite deferred | Medium | L1 uses fixture Bearer; role-matrix suite not split as portal “auth suite” |
| CI workflows on disk | Medium | `TASKS.md` claims `eval-gate.yml`; **no** `.github/workflows/*` found (2026-11-03) |
| Cost/token accounting | Low–Med | `cost_usd` hard-coded `0.0` in eval models/runner |
| Stale Phase-1 analysis | Low | `docs/eval/analysis.md` (2026-10-17) still rates L2–L9 Missing — **superseded by code** |

### 1.4 Guide mapping (high level)

| Guide chapter | LoanOps stance |
|---|---|
| Ch. 2 Observability (Phoenix/Langfuse) | **Partial** — Langfuse chosen (ADR-032); MCP instrumented; agent path incomplete |
| Ch. 3 Error analysis | **Missing** as process/product |
| Ch. 4 LLM-as-judge | **Partial** — Ragas; no calibrated custom judges with train/dev/test |
| Ch. 5 Code-based evals | **Implemented** (L1–L5, L7 core) |
| Ch. 6 RAG eval | **Partial** — answer-level Ragas; retrieval metrics per pipeline weak |
| Ch. 7 Multi-step | **Partial** — L4 trajectories; no state-level LLM judges |
| Ch. 8 Multi-turn | **Missing** |
| Ch. 9 Production / safety | **Partial** — L8 ops + safety middleware; L6 injection suite Missing |
| Ch. 10 judgy correction | **Missing** |
| Ch. 11 Improvement loop | **Partial** — promote CLI only; no root-cause → change → re-eval UX |
| Ch. 12 Human annotation | **Partial** — agreement CLI + Langfuse queues (by design); no LoanOps UI |
| Ch. 13 Cost/latency/sampling | **Partial** — L8 sampling; cost not real |

---

## 2. Gap Analysis

Status codes: **I** Implemented · **P** Partial · **M** Missing · **N** Needs improvement · **X** Not relevant

| Capability | Guide section | Current implementation | Missing | Recommended improvement | Business value | Priority |
|---|---|---|---|---|---|---|
| MCP protocol / schema / snapshots | Ch.5 + MCP-specific | L1 protocol+contracts (**I**) | Auth suite split; live matrix | Keep L1; add `auth` suite (roles, deny paths) separate from protocol | Prevents silent tool-list drift | P1 |
| MCP tool functional + errors + perf | Ch.5 | L1 functional/errors/perf (**I**) | Live SSO-gated cases | Fixture-first stays; optional `--live` nightlies | Shared MCP correctness for all clients | P1 |
| Tool discovery / selection | Ch.5, Ch.7 | L2 alternatives (**I**) | Live agent coverage of EAKG tools | Align agent tool allow-list with MCP or score “MCP-client” vs “chat-agent” separately | Wrong tool = wrong answer | P0 |
| Argument correctness | Ch.5 | L3 (**I**) | Authz-scope fitness deferred | Add scope fitness when role matrix lands | Prevents over-broad / write args | P1 |
| Trajectory / multi-step | Ch.7 | L4 constraints (**I**) | Recovery loops, redundancy metrics, full OTel tree | Score recovery on L7 faults; attach `trace_id` to reports | Explains *where* plan failed | P1 |
| Final answer grounding | Ch.4–6 | L5 deterministic + Ragas (**P**) | Custom binary judges; citation↔chunk ID binding | Keep deterministic primary; add calibrated binary judges for ambiguous cases | User trust | P0 |
| Tool failure recovery | Ch.7, Ch.11 | L7 FaultyToolsClient (**P**) | Taxonomy of recovery quality | Expand fault modes; promote recovered/failed pairs to golden | Resilience | P1 |
| Robustness / consistency | Ch.11 | L7 Wilson + variants (**I**) | Multi-model comparison harness | Optional model A/B via existing chat providers | Release confidence | P2 |
| Security / injection hard-fail | Ch.9 | Middleware + GET-only (**P**); suite **M** | Dedicated L6 cases; non-compensatory gate across layers | Build `packages.eval.safety`; hard-fail aggregate | Compliance / hard risk | P0 |
| AuthN/Z eval | Ch.9 | Fixture Bearer (**P**) | OAuth/OBO; per-user isolation tests | Server-side only; matrix suite when product auth exists | Data isolation | P1 (after auth product) |
| EAKG capability retrieval | Ch.6 | Unit/semantic tests (**P**) | Golden query→capability_id Recall@K | `packages.eval.retrieval` driver per source | Capability discovery quality | P1 |
| ApiIndex vector retrieval | Ch.6 | `test_top5_recall` (**P**) | Named golden queries in eval registry | Promote scale test into L-retrieval with report | API findability | P1 |
| Capability embeddings | Ch.6 | Rank smoke tests (**P**) | Offline Recall/MRR set | Same retrieval harness | Search quality | P2 |
| SOP / Docs retrieval | Ch.6 | Unit + Ragas context (**P**) | Doc-id Relevance@K golden | Retrieval harness + chunk attribution | Policy grounding | P0 |
| GraphRAG | Ch.6 | Service unit tests (**P**) | Community vs local search metrics | Separate metrics for global vs local | Synthesis quality | P2 |
| Engineering KG (Graphify) | Ch.6 | Graphify product (**X** as agent answer path today) | Optional if `search_code` in agent path | Eval when exposed to agent | Eng Q&A | P3 / X until exposed |
| Cross-source context graph | Ch.6–7 | Implicit via multi-tool (**M** as metric) | Evidence completeness score across sources | Outcome rubric: required evidence classes | Completeness | P2 |
| Human thumbs / ratings | Ch.12 | **M** in UI | API + store | Thin Agent API feedback → EvalStore/Langfuse score | Continuous signal | P0 |
| Inline annotations | Ch.12 | Langfuse queues (**P**); LoanOps UI **M** | Portal annotation UX | Prefer Langfuse annotation UI first; deep-link from portal | Reviewer throughput | P1 |
| Hallucination reporting | Ch.3, Ch.12 | **M** | Failure categories | Structured reason codes on feedback | Error analysis fuel | P0 |
| Dept rubrics / multi-reviewer | Ch.12, L9 | Rubric YAML + kappa (**P**) | Dept-specific rubrics; UI adjudication | Rubric files + Langfuse adjudication queue | Org scale | P2 |
| Golden promotion approval | L9 / Ch.11 | `promote` → candidates + draft registry (**P**) | PR UX; never auto-approve (already) | Portal “Promote” → opens PR checklist | Dataset integrity | P1 |
| Full execution traces | Ch.2 | MCP (**I**); agent (**M**) | AgentRuntime spans, tool args/results, citations | Instrument AgentCore via TelemetryProvider | Root-cause analysis | P0 |
| Failure clustering / root cause | Ch.3 | **M** | Open coding → axial categories | Offline notebook/CLI + optional LLM assist; store categories | Prioritized fixes | P0 |
| Missing-tool recommendations | Ch.11 | **M** | Gap ledger from fails | Join L2 misses + EAKG coverage | MCP product backlog | P2 |
| Prod sampling / SLOs | Ch.9, Ch.13 | L8 (**P**) | Richer online judges; alerts wiring | Keep deterministic online tier; sample LLM tier later | Live health | P1 |
| Judge calibration / judgy | Ch.4, Ch.10 | kappa only (**P**) | TPR/TNR + Rogan–Gladen | Add `judgy` behind Eval governance | Honest metrics | P1 |
| Eval run history / compare | Ch.11 | EvalStore runs (**P**) | Portal dashboards | Langfuse experiments + `out/eval-*.json` archive | Did we improve? | P1 |
| Cost / tokens | Ch.13 | Placeholder (**N**) | Real token/cost from providers | Emit from chat provider spans | Budget gates | P2 |
| CI eval gates | Ch.11, Ch.14 | Make targets (**P**); GH workflows **M** | Restore/add workflow YAML | `eval-mcp-l1` + L2–L5 + L9 validate on PR | Merge safety | P0 |

---

## 3. Suggested UI Features (Evaluation Portal)

**Constraint:** Avoid a second database. Use Langfuse as system of record (ADR-032). LoanOps portal = navigation + enterprise auth + domain vocabulary.

### 3.1 Near-term (Phase 1) — prefer Langfuse + light Agent API

| Feature | Approach |
|---|---|
| Trace browser | Deep-link to Langfuse trace by `trace_id` (MCP now; agent after instrumentation) |
| Offline run reports | Read `out/eval-*.json` + EvalStore run scores; table of pass/fail by layer |
| Thumbs up/down on chat answers | `POST /feedback` → EvalStore `ScoreRecord` + optional annotation queue item |
| Structured fail reasons | Enum: `wrong_tool`, `bad_args`, `retrieval_miss`, `ungrounded`, `hallucination`, `unsafe`, `ux_clarity`, `other` |
| Golden candidate inbox | List `data/eval/candidates/` + draft registry; “Open PR” checklist |
| Layer health strip | Last CI/local report per L1–L5, L7–L9 (L6 when built) |

### 3.2 Phase 2 — Human review workbench

| Feature | Approach |
|---|---|
| Side-by-side review | Prompt / tools / evidence / answer / rubric checklist |
| Multi-reviewer | Two labels required → disagreement → `loanops-adjudication` (already named in L9 docs) |
| Inline span comments | Prefer Langfuse comments API; mirror summary in portal |
| Rubric picker | Bind to `data/eval/rubrics/*.yaml` versions |
| Dataset manager | Filter registry by layer/status/stale; duplicate Jaccard warnings (validate already warns) |

### 3.3 Phase 3 — Failure intelligence

| Feature | Approach |
|---|---|
| Failure taxonomy board | Counts by category over window (guide Ch. 3) |
| Component attribution | Which layer failed first (L2 vs L3 vs L5 vs retrieval) |
| Before/after compare | Experiment run A vs B on same dataset |
| Missing capability suggestions | Aggregate L2 unknown/missing tools + EAKG gaps |
| Ops vs offline twin dashboards | Already specified in `layer8-operations.md` — expose in portal |

**Not recommended:** Building a full Phoenix/Braintrust clone inside React. Reuse Langfuse UI for annotation queues and trace drill-down.

---

## 4. Recommended Libraries and Repositories

| Project | URL | Relevant functionality | What to reuse | Integration complexity | License / maintenance |
|---|---|---|---|---|---|
| **Langfuse** (already) | https://github.com/langfuse/langfuse | Traces, datasets, scores, annotation queues, environments | Keep as EvalStore + Telemetry backend; UI for review | Low (done via provider) | OSS; self-host already in CONTEXT |
| **Ragas** (already) | https://github.com/explodinggradients/ragas | Faithfulness / relevancy | Keep pinned for L5; do not expand as only retrieval metric | Low | Apache-2.0; pin version |
| **judgy** | https://github.com/ai-evals-course/judgy | Judge bias correction + CI | Wire into L9 `calibrate` after human labels exist | Low | MIT; small API surface |
| **OpenTelemetry** (already) | https://opentelemetry.io | Span model | AgentCore instrumentation consistent with MCP | Medium | Industry standard |
| **Promptfoo** | https://github.com/promptfoo/promptfoo | YAML scenario runner / CI | **Optional only** if team wants red-team YAML; do **not** replace L1–L9 | Medium–High (duplicate SoR risk) | MIT; note ownership changes per guide |
| **Arize Phoenix** | https://github.com/Arize-AI/phoenix | Self-host traces + evals | **Skip** as primary — duplicates Langfuse (ADR-032) | High (second platform) | ELv2 |
| **DeepEval** | https://github.com/confident-ai/deepeval | Broad metric kit | Cherry-pick ideas; avoid full framework | Medium | Apache-2.0 |
| **Inspect AI** (UK AISI) | https://github.com/UKGovernmentBEIS/inspect_ai | Agent traj evals | Patterns for multi-turn; not drop-in | High | Apache-2.0 |
| **Braintrust / LangSmith** | SaaS | Nice UI | **Not relevant** while Langfuse + local-first holds | — | Paid / lock-in |
| **rank_bm25** | https://github.com/dorianbrown/rank_bm25 | Baseline retriever | Only if building synthetic RAG baselines for diagnosis | Low | Apache-2.0 |
| **ai-evals-course/evals-skills** | https://github.com/ai-evals-course/evals-skills | Agent skills for product evals | Process/playbooks for error analysis — not runtime dep | None | Check repo license |

**Reuse first (already in-repo):** pytest, FastMCP/`mcp`, `packages.safety`, EvalStore, TelemetryProvider, EAKG `review.py` patterns (approval log), ApiIndex recall test pattern.

---

## 5. Target Architecture

```text
                    ┌─────────────────────────────────────────┐
                    │         Evaluation Portal (thin)         │
                    │  feedback · reports · promote · links    │
                    └──────────────┬──────────────────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
    Agent API /chat          Eval CLIs (make)        Langfuse UI
    + /feedback              L1–L5, L6*, L7–L9       annotation queues
           │                       │                       │
           ▼                       ▼                       ▼
    TelemetryProvider  ←────  EvalStoreProvider  ────→  datasets/runs/scores
    (prod env)                (eval env)                 traces (shared backend)
           │
           ├─ MCP server spans (today)
           └─ AgentCore turn spans (target)
           
Offline scorers (deterministic, in-repo):
  L1 MCP · L2 select · L3 args · L4 traj · L5 outcome · L6 safety*
  Retrieval drivers (per corpus) · L7 robustness

Online:
  L8 sample deterministic → queue fails
  Optional tier-2 LLM judge (calibrated) on sample

Governance:
  registry.jsonl + rubrics (git SoT) → sync mirror → promote candidates → PR
```

### How surfaces work together

1. **MCP evaluation** — L1 offline + L8 live SLOs per `mcp.client_name` (any consumer).
2. **Agent evaluation** — L2–L5/L7 on trajectories from `run_agent_turn` (canned or live); same MCP tools when `TOOLS_CLIENT__PROVIDER=mcp`.
3. **Retrieval evaluation** — Independent harness per knowledge pipeline; failures attribute to retrieval before blaming the LLM.
4. **Human review** — Production/sampled fails → Langfuse queue → labels → kappa/judgy → promote candidates → git PR → L9 validate.
5. **Production monitoring** — `ops.*` scores never mix with `eval.*` (already locked).

### Explicit non-goals (preserve architecture)

- No new primary datastore for eval.
- No lowering `thresholds.py`.
- No client-side MCP auth enforcement.
- No second observability platform unless Langfuse is rejected org-wide (**ASSUMPTION:** Langfuse remains approved).

---

## 6. Implementation Roadmap

### Phase 1 — Essential (closes “pass/fail only” → “which component”)

**Dependencies:** None blocking for offline work; Langfuse optional (jsonl default).

| Deliverable | Notes |
|---|---|
| Instrument AgentCore turns via `TelemetryProvider` | Approval may be needed (AGENTS.md observability); highest leverage |
| Layer 6 hard-fail suite + aggregate gate | Injection via tool results, write attempts, scope bypass; non-compensatory |
| Unify report schema with `trace_id` + first failing layer | Extend reports; don’t break golden thresholds |
| Retrieval eval package (Docs + ApiIndex + EAKG first) | Recall@K / MRR / evidence completeness; reuse ApiIndex pattern |
| Chat feedback API → EvalStore scores | Thumbs + reason codes |
| CI workflows for `eval-mcp-l1`, L2–L5, L9 validate | Fix missing `.github/workflows` |
| Refresh `docs/eval/analysis.md` status table | Prevent stale gap ratings |
| Align agent tool list vs MCP (product decision) | Either expose EAKG tools to agent or document dual surfaces |

**Exit criteria:** Failed run answers *layer + tool/retrieval/answer*; feedback lands in EvalStore; L6 blocks unsafe passes.

### Phase 2 — Advanced evaluation & human review

| Deliverable | Notes |
|---|---|
| Evaluation Portal MVP | Report browser + Langfuse deep-links + feedback inbox + promote checklist |
| Multi-reviewer adjudication UX | Wire existing queues + agreement CLI |
| Calibrated binary LLM judges + `judgy` | Train/dev/test split; TPR/TNR gates before prod use |
| Error-analysis CLI | Open-coding notes → axial categories → counts (guide Ch. 3) |
| Expand L7 live faults + paraphrase generation | Keep canned CI path |
| AuthZ matrix suite (when product auth ready) | Server-side only |

**Exit criteria:** Reviewer can promote a prod failure to draft golden via governed path; judge trusted only when calibrated.

### Phase 3 — Continuous evaluation & production intelligence

| Deliverable | Notes |
|---|---|
| Failure taxonomy dashboard | Category trends, component attribution |
| Missing-tool / missing-SOP recommender | Joins eval fails + EAKG/ApiIndex coverage |
| Model/prompt A/B with regression gates | Guide Ch. 11 |
| Multi-turn session eval | Strategy 1 then 2 from guide Ch. 8 |
| Real cost/token gates | From provider spans |
| GraphRAG + Graphify retrieval slices | When those paths are agent-critical |
| Tiered online eval (code → cheap judge → sample strong judge) | Guide Ch. 13 |

**Exit criteria:** Weekly improvement loop: sample → label → fix → regression green → corrected prod rate reported.

---

## 7. Classification summary (A–F ask)

### A. MCP Evaluation

| Item | Class |
|---|---|
| Protocol / schema | Implemented |
| Tool discovery contracts | Implemented |
| Functional / errors / perf | Implemented |
| AuthZ / OAuth matrix | Partial / deferred |
| Security regression (injection suite) | Missing (policy partial) |

### B. AI Agent Evaluation

| Item | Class |
|---|---|
| Tool selection / planning (L2/L4) | Implemented (canned-strong) |
| Argument correctness | Implemented |
| Final answer grounding | Partial (good deterministic; weak custom judge) |
| Recovery from tool failures | Partial (L7) |
| Multi-turn | Missing |
| Consistency / robustness | Implemented (L7) |
| Edge-case discovery process | Missing |
| Full trajectory traces | Needs improvement (MCP yes, agent no) |

### C. Retrieval / Knowledge

| Pipeline | Class |
|---|---|
| EAKG discovery | Partial |
| ApiIndex vectors | Partial (best of set) |
| Capability embeddings | Partial |
| SOP docs | Partial |
| GraphRAG | Partial |
| Engineering KG | Not relevant to agent eval until in tool path |
| Cross-source evidence completeness | Missing |

### D. Human Feedback / Review

| Item | Class |
|---|---|
| Thumbs / structured ratings in product | Missing |
| Annotations / queues | Partial (Langfuse/CLI) |
| Failure categorization | Missing |
| Dept rubrics | Partial (files exist; not dept-scaled) |
| Multi-reviewer / disagreement | Partial (kappa CLI) |
| Approval before golden | Partial (promote→draft; git PR assumed) |

### E. Error Analysis / Continuous Improvement

| Item | Class |
|---|---|
| Complete traces | Partial |
| Group recurring failures | Missing |
| Root-cause attribution by component | Partial (layers help; not automated) |
| Recommend tool add/remove | Missing |
| Prod fail → golden | Partial |
| Regression after fix | Partial (make targets; CI gap) |

### F. Production Evaluation

| Item | Class |
|---|---|
| Historical run compare | Partial |
| Judge calibration | Partial (kappa only) |
| Inter-reviewer agreement | Implemented (library-level) |
| Cost/latency/reliability | Partial (latency SLOs; cost stub) |
| Prod sampling | Partial |
| Release gates | Partial (local make; CI missing on disk) |

---

## 8. Verified vs assumption vs recommendation

| Kind | Examples |
|---|---|
| **Verified** | L1–L5/L7–L9 packages exist; no L6 package; no eval UI; AgentCore untraced; ADR-032; no `.github/workflows`; agent 4 vs MCP 10 tools |
| **Assumption** | Self-hosted Langfuse remains org standard; live `make eval` still SSO-gated (per TASKS); enterprise GET side effects not fully audited |
| **Recommendation** | Instrument agent; build L6; retrieval harness; feedback API; CI; portal thin over Langfuse; add `judgy`; do not adopt Phoenix/Promptfoo as SoR |

---

## 9. Immediate next actions (when implementation approved)

1. ADR/approval: AgentCore → TelemetryProvider spans.  
2. Spec stub: Layer 6 safety eval + retrieval eval harness (Promp under `.ai/specs/`).  
3. Product decision: agent tool surface vs MCP-complete.  
4. Ship `POST /feedback` + reason codes (smallest closed loop).  
5. Restore CI eval gates on GitHub.

---

*Supersedes gap ratings in `docs/eval/analysis.md` §8 for L2–L9 “Missing” — those layers are now code-complete; treat analysis.md as historical discovery plus still-valid auth/telemetry unknowns in §9.*
