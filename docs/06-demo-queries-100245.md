# Demo queries — live Loan Services (Path A)

Config assumed:

```
TOOLS_CLIENT__PROVIDER=modular
AGENT_ROLE=system
SSE__USE_FIXTURE=false
SSE__FIXTURE_PATH=data/sse-loanservices-catalog.json
SSE__API_BASE_URL=https://loanservicesapi-plaisse-dev.pnmac.com
SSE__API_KEY=<dev Auth0 bearer>
SSE__SWAGGER_LINKS=[{"id":"loanservices","label":"LoanServices","url":"https://loanservicesapi-plaisse-dev.pnmac.com/swagger/1.0/swagger.json"}]
```

Use a real loan id known in Loan Services (example: `1000002245`).

---

## 1. Loan summary (SSE)

> Show me the loan summary for 1000002245

Expect: `search_sse_apis` → `call_sse_api` (`getLoanSummary`). Citation `tool:call_sse_api`.
Live URL: `…/api/Loans/1000002245/Summary` status 200.

## 2. Payment schedules (SSE)

> What are the payment schedules for loan 1000002245?

Expect: `search_sse_apis` → `call_sse_api` (`getPaymentSchedules`). Citation `tool:call_sse_api`.

## 3. Escrow (SSE)

> Get escrow details for loan 1000002245

Expect: `call_sse_api` for `getEscrows` (after search).

## 4. Borrower summary (SSE)

> What's the borrower summary for loan 1000002245?

Expect: `getBorrowerSummary` via `call_sse_api`.

---

## Not used

- `apps/tools_api` / `lookup_loan` / `get_payment_schedule` — **removed**
- SQL `get_customer_servicing_summary` — not on `system` role

---

## Run one

```powershell
$body = @{
  message    = "Show me the loan summary for 1000002245"
  session_id = "demo-sse"
  rep_id     = "rep-demo"
} | ConvertTo-Json
Invoke-WebRequest -Method Post -Uri "http://127.0.0.1:8000/chat" `
  -ContentType "application/json" -Body $body
```
