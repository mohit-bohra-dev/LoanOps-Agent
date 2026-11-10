# Question-type checklist

**Date:** 2026-11-05  
**Loan under test:** `1000002245`  
**Run log:** [test-queries.txt](./test-queries.txt)  
**Multi-user:** [eval/multi-user-scenario-testing.md](./eval/multi-user-scenario-testing.md) — Eval Portal → Scenarios + Isolated chat

Current stack: `search_sse_apis` (OpenAPI-first) then `call_sse_api` (GET only), plus the discovery nudge.

`/chat` tools: `search_sse_apis`, `list_sse_apis`, `call_sse_api`, `describe_application`,
`search_capabilities`, `explain_capability`, `find_providers`, `impact_of_change`,
`search_code`, `search_docs`.

Flip `[ ]` → `[x]` only after a logged run in `test-queries.txt`. Use `[~]` for PARTIAL.

---

## Answers well (question types)

- [x] **Direct live-data ask** — "Get escrow details for loan 1000002245"  
  Search finds `GetEscrowByLoanNumber`, `call_sse_api` returns JSON. See #3 / S2. Trace `655680b6746c1f6e5bf6f10eed0891ca`.
- [ ] **Named operation** — "Call GetLoanSummary for 1000002245"  
  Op id already in the question; ranking barely matters. Not logged yet.
- [x] **Single-hop loan fact** — "Show payment schedule for loan 1000002245"  
  `search_sse_apis` → `call_sse_api` `loanservices:GET_api_loans_id_paymentschedules` → 200. Trace `0246a0efa79f2a1f8518917e873c3b00`.

## Often wrong or incomplete

- [~] **Why / explain a change** — "Why did escrow jump on loan 1000002245?" (F1)  
  Auto `call_sse_api`, wrong op `loanservices:GET_api_escrows_id` → 404. Trace in F1 log.
- [ ] **Vague domain word** — "escrow", "fees", "notes"  
  Flat OpenAPI search mixes bulk-upload / home routes with the real loan GET.
- [ ] **Multi-step / process** — "What must happen before escrow analysis?"  
  Process edges exist; search does not walk them. Not wired (no MCP process tool).
- [ ] **Compare / compute** — "How much did escrow change vs last month?"  
  One call, no second fetch, no math over history.
- [ ] **Writes** — "Add a note", "start a plan"  
  `call_sse_api` is GET-only. Non-GET rejected.
- [ ] **No loan id** — "Why do escrows jump in CA?"  
  Should come from `search_docs`. Path weak; model often skips.

---

## Smoke set (#1–#5)

- [~] **#1 Loan summary** — "Show me the loan summary for 1000002245"  
  PARTIAL: tools OK (`GET_api_loans_id_summary` 200); final answer refused. Trace `08e8a451585d51fd643ae72ec7607c0f`.
- [~] **#2 Payment schedule** — "Show payment schedule for loan 1000002245"  
  Was OK `0246a0efa79f2a1f8518917e873c3b00`. Retest 2026-11-10: correct op, SSE **500**. Trace `72fc288b842d8eee8981e9296fb8a4da`.
- [x] **#3 Escrow details** — "Get escrow details for loan 1000002245"  
  OK when op resolves to escrow `GetEscrowByLoanNumber`. Trace `655680b6746c1f6e5bf6f10eed0891ca`.
- [ ] **#4 Fees** — "What fees apply for loan 1000002245?"  
  UNTESTED.
- [x] **#5 GetLoanSummary ownership** — "Which app provides GetLoanSummary? Explain it."  
  OK: `find_providers` → `explain_capability`. Trace `039846ee18abc4d87f721e2341c47349`.

## ENG — interface + AST (#6–#9)

- [x] **#6 Outbound proxies** — "Does loanservices use outbound proxies? List them."  
  OK: `describe_application`. BulkUploadProxy, LampApiProxy, EscrowApiProxy, CashApiProxy, LafaApiProxy. Trace `604f30b868e2822d51b2a673aa2ad71f`.
- [x] **#7 App interface** — "Describe the loanservices application interface (proxies, packages, topics)."  
  OK: `describe_application`. Trace `de7ff71ca11bc5d8d091687cdf6865a4`.
- [~] **#8 Facades** — "Does loanservices use any Facades? List them."  
  PARTIAL: `search_code` fired; engineering graph missing (`EAKG__ENGINEERING_GRAPH`).  
  Retest isolated 2026-11-05: same. Trace `9f3eea5de58bc9cb0fd7261a79e76590`.
- [x] **#9 Impact** — "Which applications depend on the escrow API?"  
  OK: `impact_of_change` (empty dependents). Trace `8b0c136ada27ee1243f83d203855e5e3`.

---

## Source coverage (S1–S12) — every reachable knowledge source

| # | Source | Query | Status |
|---|---|---|---|
| S1 | Live loan API | Show me the loan summary for 1000002245 | [~] PARTIAL — tools 200; answer refused — `08e8a451…` |
| S2 | Live loan API (escrow) | Get escrow details for loan 1000002245 | [x] OK — `655680b6…` |
| S3 | ApiIndex search only | Which API returns the payment schedule for a loan? Don't call it. | [ ] UNTESTED |
| S4 | Catalog listing | List the operations available in the Fees app. | [ ] UNTESTED |
| S5 | EAKG block in search | Which application provides escrow disbursement capabilities? | [ ] UNTESTED |
| S6 | App interface | Does loanservices use outbound proxies? List them. | [x] OK — `604f30b8…` |
| S7 | App interface (escrow) | Which SDK packages and event topics does escrow use? | [ ] UNTESTED |
| S8 | SOP docs | What is the procedure for an escrow dispute? | [ ] UNTESTED |
| S9 | SOP docs (state) | What does the California policy say about late fees? | [~] PARTIAL — wrong hit / refuse — `80c4bf0b…` |
| S10 | SOP docs (hardship) | What forbearance options exist for military borrowers (SCRA)? | [ ] UNTESTED |
| S11 | Docs + live API | Loan 1000002245 escrow jumped. Pull escrow + annual analysis SOP. | [ ] UNTESTED |
| S12 | Interface + docs | Which apps does loanservices call outbound, and is there an SOP for escrow disbursements? | [~] PARTIAL — describe OK; no escrow-disbursements.md — `de5ae4eb…` |

### S-detail checkboxes

- [~] **S1** Live loan API — loan summary  
  PARTIAL: `search_sse_apis` → `call_sse_api` Summary 200; empty answer / refusal after 2 attempts. Trace `08e8a451585d51fd643ae72ec7607c0f`.
- [x] **S2** Live loan API — escrow  
  Trace `655680b6746c1f6e5bf6f10eed0891ca`.
- [ ] **S3** ApiIndex only — payment schedule API name, no invoke  
  Expect: `search_sse_apis` only.
- [ ] **S4** Catalog — Fees ops  
  Expect: `list_sse_apis` (Fees).
- [ ] **S5** EAKG capability block — escrow disbursement app  
  Expect: `search_sse_apis` EAKG block (or `search_capabilities`).
- [x] **S6** Interface — loanservices proxies  
  Trace `604f30b868e2822d51b2a673aa2ad71f`.
- [ ] **S7** Interface — escrow packages/topics  
  Expect: `describe_application` escrow.
- [ ] **S8** Docs — escrow dispute SOP  
  Expect: `search_docs` → `escrow/escrow-dispute.md`.
- [~] **S9** Docs — California late fees  
  PARTIAL: hit disaster-forbearance, not `state-specific/california-policy.md`. Trace `80c4bf0b1518fe83665cad2b435610c5`.
- [ ] **S10** Docs — military SCRA forbearance  
  Expect: `search_docs` → `hardship/military-scra.md`.
- [ ] **S11** Combo — escrow live + annual analysis SOP  
  Expect: `call_sse_api` + `search_docs`.
- [~] **S12** Combo — loanservices outbound + escrow disbursements SOP  
  PARTIAL: `describe_application` OK (BulkUpload/Lamp/EscrowManager/Cash/Lafa). `search_docs` missed `escrow/escrow-disbursements.md` (hit annual-analysis + IOE). Trace `de5ae4eb8ba4328c586f823b8e17bb46`.

---

## Tool inventory (what `/chat` can call)

- [x] `search_sse_apis` — OpenAPI + optional EAKG capability block
- [x] `list_sse_apis` — catalog listing (S4 untested)
- [x] `call_sse_api` — live GET
- [x] `describe_application` — proxies / packages / topics
- [ ] `search_capabilities` — advertised; no dedicated logged query yet (S5 may use it)
- [x] `explain_capability` — used on #5
- [x] `find_providers` — used on #5
- [x] `impact_of_change` — used on #9
- [~] `search_code` — called on #8; needs engineering graph
- [~] `search_docs` — works; S9 ranking weak

## Not wired (cannot check via `/chat` yet)

- [ ] Process KG (`hasStep` / BusinessProcess) — no MCP or agent tool
- [ ] GraphRAG community summaries — `GRAPHRAG__ENABLED` default off; wraps `search_docs` only when on
