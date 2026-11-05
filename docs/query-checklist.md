# Question-type checklist

**Date:** 2026-11-05  
**Loan under test:** `1000002245`  
**Run log:** [test-queries.txt](./test-queries.txt)

Current stack: `search_sse_apis` (OpenAPI-first) then `call_sse_api` (GET only), plus the discovery nudge.

`/chat` tools: `search_sse_apis`, `list_sse_apis`, `call_sse_api`, `describe_application`,
`search_capabilities`, `explain_capability`, `find_providers`, `impact_of_change`,
`search_code`, `search_docs`.

**Good today:** one clear GET, an obvious operation name, and a loan number. Flip a box only after a logged run in `test-queries.txt`.

## Answers well

- [x] **Direct live-data ask** — "Get escrow details for loan 1000002245"  
  Verified: search finds `GetEscrowByLoanNumber`, `call_sse_api` returns JSON. See #3.
- [ ] **Named operation** — "Call GetLoanSummary for 1000002245"  
  Operation id is already in the question, so ranking barely matters. Not logged yet.
- [x] **Single-hop loan fact** — "Show payment schedule for loan 1000002245"  
  2026-11-05: `search_sse_apis` → `call_sse_api` `loanservices:GET_api_loans_id_paymentschedules` → 200. Trace `0246a0efa79f2a1f8518917e873c3b00`. Query 1 (loan summary) still untested.

## Often wrong or incomplete

- [ ] **Why / explain a change** — "Why did escrow jump on loan 1000002245?"  
  Partial (F1): auto `call_sse_api`, wrong op `loanservices:GET_api_escrows_id` → 404.  
  A correct payload still would not explain "why" (needs docs or a process; `search_docs` is optional).
- [ ] **Vague domain word** — "escrow", "fees", "notes"  
  Many similar operations. Flat OpenAPI search mixes bulk-upload and home routes with the real loan GET.
- [ ] **Multi-step / process** — "What must happen before escrow analysis?"  
  Process edges exist (`hasStep`, `dependsOn`) but search does not walk them. Expand step not wired.
- [ ] **Compare / compute** — "How much did escrow change vs last month?"  
  One call, no second fetch, no math over history.
- [ ] **Writes** — "Add a note", "start a plan"  
  `call_sse_api` is GET-only. Non-GET rejected.
- [ ] **No loan id** — "Why do escrows jump in CA?"  
  No loan to call. Should come from `search_docs` (SOPs). Path is weak; the model often skips it.

## EAKG / engineering (now on `/chat`)

- [x] **"Which app owns GetLoanSummary?"** — `find_providers` + `explain_capability`  
  Query 5 OK 2026-11-05. loanservices GET. Trace `039846ee18abc4d87f721e2341c47349`.
- [x] **"Does loanservices use outbound proxies?"** — `describe_application`  
  Query 6 OK. Proxies: BulkUploadProxy, LampApiProxy, EscrowApiProxy, CashApiProxy, LafaApiProxy. Trace `604f30b868e2822d51b2a673aa2ad71f`.
- [x] **"Describe loanservices interface"** — `describe_application`  
  Query 7 OK. Trace `de7ff71ca11bc5d8d091687cdf6865a4`.
- [ ] **"Does loanservices use Facades?"** — `search_code`  
  Query 8 PARTIAL: tool fired; engineering graph missing (`EAKG__ENGINEERING_GRAPH`). Trace `d65d1a76dd2f9fc8b4153040c130978a`.
- [x] **"Who depends on escrow API?"** — `impact_of_change`  
  Query 9 OK (empty dependents). Trace `8b0c136ada27ee1243f83d203855e5e3`.
