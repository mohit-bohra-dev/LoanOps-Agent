# Eval layers — plain English

Nine layers grade the MCP tools and the agent. Audience: Engineering, QA, Ops, Product, Compliance (AI Evaluation Portal taxonomy).

**Sources:** original Phase 1 brief + portal lock-in from prior agent chat `3a18cec4-9ed5-4ea8-ad75-a390aecd7d45` (nine-layer taxonomy + L1/L2 plain-English explainers); design rules also in [analysis.md](analysis.md) Appendix C.

Lower layers = plumbing. Higher layers = “was the answer safe and still good next week?”

| # | Name (portal) | One-line question |
|---|---|---|
| 1 | MCP server | Does the tool server speak MCP correctly and behave? |
| 2 | Discoverability / tool selection | Did the agent pick the right tool(s)? |
| 3 | Arguments | Were the inputs to those tools correct and safe? |
| 4 | Trajectory | Was the multi-step *path* valid? |
| 5 | Outcomes | Was the final answer right and grounded? |
| 6 | Safety / security | Did anything unsafe slip through? (**hard fail**) |
| 7 | Robustness | Still good across repeats / noise? |
| 8 | Operations | Live prod health ≠ offline exam scores |
| 9 | Evaluation governance | Who owns the test book? |

**Kitchen analogy:** (1) oven works → (2) right pan → (3) right ingredients → (4) sane recipe order → (5) tastes right → (6) nothing poisonous → (7) still good on a bad day → (8) restaurant health scores vs kitchen drills → (9) who approved the recipe book.

Security (6) is **non-compensatory**: a fail there fails the run; high scores elsewhere cannot wash it out.

---

## Layer 1 — MCP server

**One line:** Is the MCP server healthy — without an AI model, and without an Auth exam.

**Question:** Can a client handshake, list tools, and call them without the protocol or server lying?

### What it checks (from the brief)

- Protocol conformance for the MCP revision the code targets
- Schema validity; snapshot regression of tool lists / responses
- Per-tool functional tests + edge cases
- Error handling: invalid args, upstream failure, timeout, rate limit
- Latency and concurrency
- (Auth / OAuth / per-user authorization: **deferred** from the current suite — fixture Bearer is harness plumbing only)

### Locked portal rules

- **Split suites** — do not mix: (a) protocol / JSON-RPC, (b) tool business logic + schema, (c) authorization, (d) performance/concurrency
- **Protocol error ≠ tool error.** Malformed request / unknown method → JSON-RPC error. Tool ran but failed operationally → `CallToolResult` with `isError: true`. Test both.

### Built suites today

| Suite | Plain meaning |
|---|---|
| `protocol` | Handshake, bad JSON, unknown method, bad params, unknown tool |
| `contracts` | All registered tools, schemas, `readOnlyHint`, GET-only policy, snapshots |
| `functional` | Happy path / empty / fixture results |
| `errors` | Upstream fail, exception, timeout, rate-limit → clear failure |
| `perf` | Concurrent isolation, p50/p95, payload budgets |

**Status:** Built. Docs: [layer1-mcp.md](layer1-mcp.md). Run: `make eval-mcp-l1`.

---

## Layer 2 — Discoverability / tool selection

**One line:** Grades *which tools were used* — not wire protocol (L1), not final reply text (L5).

**Question:** For this user ask, did we call the tools we should — and not the ones we shouldn’t?

### Simple picture

User: *“Why did escrow jump on loan 100245?”*

A good agent might call:

1. `search_sse_apis` — find the API  
2. `call_sse_api` — get loan/escrow data  
3. `search_docs` — policy explanation  

Layer 2 scores that **choice of tool names**, not the English answer.

### What it checks

| Check | Plain meaning |
|---|---|
| Right tool(s) | Scenario needs live data → must use something like `call_sse_api` |
| Alternatives OK | Docs-first vs APIs-first can both be valid — don’t fail a legal path |
| No call when none needed | Refusal / small talk → no tool spam |
| Similar-tool confusion | e.g. `search_sse_apis` vs `search_capabilities` — right family |
| Forbidden tools | Must not call mutating / write tools (v1 read-only) |
| Unknown names | Invented tool name fails |

### Locked portal rule

Score against **allowed tool sets / alternatives**, not only one exact tool list.

### LLM?

- **Scoring** = deterministic (compare observed names vs expectation).
- **Producing** the calls usually needs an agent — or feed **canned** recorded trajectories (default runner mode).

**Status:** Built. Docs: [layer2-tool-selection.md](layer2-tool-selection.md). Run: `make eval-l2`.

---

## Layer 3 — Arguments

**One line:** Right *inputs* to tools — not which tools (L2), not call order (L4), not answer text (L5).

**Question:** Once tools are chosen, are parameters correct (and safe)?

### What it checks (brief + portal)

- Required fields, types, values grounded in the user request or prior tool results
- Correct IDs, dates, units; no over-broad queries
- **Side-effect class** — read vs write; v1 write must fail policy (GET / no body)
- Authorization-scope fitness for args (portal taxonomy) — **role matrix deferred** with Layer 1 Auth; current scorer focuses on fields/types/values + GET/no-body

**Status:** Built. Docs: [layer3-arguments.md](layer3-arguments.md). Run: `python -m packages.eval.arguments` / `make eval-l3` if present.

---

## Layer 4 — Trajectory

**One line:** Was the *path* of tool calls valid? Ordered tool **names** only.

**Question:** Did the multi-step run follow a *valid* path — required steps, dependencies, forbidden actions?

### What it checks (brief + portal)

| Check | Example |
|---|---|
| Required steps | Must call `search_sse_apis` and `call_sse_api` at least once |
| Dependencies | First search before first `call_sse_api` |
| Forbidden actions | Must not call listed tools |
| Alt path sets | Any one valid constraint set is enough |
| Unknown tools | Invented name fails |
| Refusal | Expect no tools → empty list only |

Also in the original brief (full vision): capture runs as OTel spans (query, each call, args, results, errors, timing, parent-child, trace ID); step count; redundant calls; loops; recovery; termination. **Trace capture / Langfuse wiring deferred** until agent instrumentation is approved.

### Locked portal rule

**Do not** require one exact sequence when multiple paths are valid (e.g. docs-before-API vs API-before-docs). Prefer required steps + deps + forbidden actions + acceptable outcomes.

**Not** Layer 2 (set of tools, order ignored), Layer 3 (args), Layer 5 (answer text), or Layer 1 (protocol).

**Status:** Built. Docs: [layer4-trajectory.md](layer4-trajectory.md). Run: `make eval-l4`.

---

## Layer 5 — Outcomes

**One line:** Did the user get a correct, grounded answer?

**Question:** Given what tools returned, is the final answer complete, relevant, clear — with right refusals / clarifications?

### What it checks

- Task completion; groundedness in tool results
- Citations (`policy:` / `tool:`) present and tied to real retrieval
- Optional Ragas faithfulness / answer relevance (pinned model when used)
- Refusal / escalation correctness on those golden items
- When a task can change data: verify **business end state** (v1 mostly read-only → still verify answer vs tool strings)

### Locked portal rule

**Include a small L5 set in the PoC.** An agent can pass L1–L4 and still give a wrong answer. Score groundedness + completeness vs tool-result strings (v1 writes out of scope).

**Status:** Built (deterministic canned + optional `--live` structural). Docs: [layer5-outcomes.md](layer5-outcomes.md). Run: `make eval-l5`. Existing `make eval` still owns Ragas / sacred thresholds — **do not lower**. Business-state mutation checks still out of scope.

---

## Layer 6 — Safety and security

**One line:** Unsafe = hard fail. Cannot average it away.

**Question:** Prompt injection via tool results, tool poisoning, excessive agency, authz bypass, cross-user leakage, PII/secrets exposure, policy adherence, cross-server attacks, auditability?

### Locked portal rule

Security failures are **hard / non-compensatory**.

**Status:** Partial (safety middleware unit tests + MCP GET-only / scopes). Dedicated injection suite + non-compensatory gate still to finish. Auth matrix largely deferred here with L1.

---

## Layer 7 — Robustness

**One line:** One lucky pass is not enough when the model wobbles.

**Question:** Across N repeats, paraphrase variants, malformed inputs, long multi-turn, degraded downstream, model/prompt regressions — does pass-rate stay above the bar?

### Locked portal rule

Nondeterministic cases: **N repeats + defined pass-rate threshold**.

**Status:** Missing (no N-repeat harness yet).

---

## Layer 8 — Operations (production monitoring)

**One line:** Classroom test ≠ restaurant health inspection.

**Question:** Sampling/scoring of production traces; latency, cost, tokens, error/success rates, drift, alert thresholds that feed release gates.

### Locked portal rule

**Separate** production monitoring metrics from offline evaluation scores (connected dashboards, different stores/gates).

**Status:** Missing as an eval layer (telemetry hooks exist; no prod-vs-offline split / alert thresholds in-repo).

---

## Layer 9 — Evaluation governance

**One line:** Golden sets are product artifacts, not throwaway files.

**Question:** LLM-judge calibration vs humans; inter-reviewer agreement; adjudication; duplicate/stale case detection; Golden Dataset versioning; reviewer approval before promotion; traceability from case → source trace.

### Locked portal rule

Dataset approval, **rubric versioning**, reviewer disagreement / adjudication.

**Status:** Missing (no promotion workflow / rubric versions in-repo). Phase 3 in the original brief covers Golden JSONL fields, promotion PR flow, CI gates, `evals run --layer`, department reports.

---

## How they stack

```text
L9 governance ──────── who may change the tests
L8 operations ──────── live monitoring (separate from offline)
L7 robustness ──────── repeat flaky cases
L6 security ────────── hard fail (non-compensatory)
L5 outcomes ────────── answer quality vs tool evidence
L4 trajectory ──────── valid multi-step path
L3 arguments ───────── right inputs
L2 selection ───────── right tools
L1 MCP server ──────── protocol + tool contracts
```

### PoC build order (locked)

1. L1a/b deterministic MCP  
2. L2 + L3 tool pick + args  
3. L4 constraint trajectories (+ tracing later)  
4. Small L5 outcomes  
5. High-priority L6 injection / policy hard-fails  
6. Later: L7–L9  

### Executable golden cases

Each case should declare `eval_methods[]` (which checkers run), e.g.:

| Case idea | Methods |
|---|---|
| Invalid MCP tool arguments | deterministic assert |
| Correct API for a payment query | expected tools (allow alternatives) |
| Correct payment date in final answer | grounding + outcome |
| Prompt injection in API response | security hard-fail |
| Ambiguous business request | human rubric or calibrated LLM judge |

### Practical run order today

1. `make eval-mcp-l1` — L1  
2. `make eval-l2` — L2  
3. `make eval-l3` — L3  
4. `make eval-l4` — L4  
5. `make eval` — L5-ish golden (citations / refusal / optional Ragas)

---

## Related docs

| Doc | Role |
|---|---|
| [analysis.md](analysis.md) | Phase 1 discovery + Appendix C taxonomy |
| [layer1-mcp.md](layer1-mcp.md) | L1 how-to |
| [layer2-tool-selection.md](layer2-tool-selection.md) | L2 how-to |
| [layer3-arguments.md](layer3-arguments.md) | L3 how-to |
| [layer4-trajectory.md](layer4-trajectory.md) | L4 how-to |
| `packages/eval/thresholds.py` | Sacred golden thresholds (do not lower) |
