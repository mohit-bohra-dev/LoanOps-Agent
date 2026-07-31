# Demo queries — Loan 100245

Config assumed:

```
DATA__LOAN_SOURCE=mock
DATA__SOP_SOURCE=confluence
DATA__SOP_CONFLUENCE_MODE=cache
```

Loan 100245 fixture facts (for checking answers):

| Field | Value |
|-------|-------|
| Borrower | Alex Rivera |
| State | CA |
| Status | active, 0 days delinquent |
| UPB | $324,188.42 |
| Total monthly payment | $2,207.97 (P&I $1,592.67 + escrow $615.30) |
| Escrow balance | $1,500.00 |
| Escrow change | +$20.00 effective 2026-06-01 |
| Escrow drivers | county_tax ($369.18), hazard_insurance ($246.12) |
| Last / next analysis | 2026-05-01 / 2027-05-01 |
| Late charge fee | $35.00, grace end 2026-06-01 |

---

## 1. Account snapshot (tool only)

> Borrower on the line about loan 100245 — pull the account and tell me where the payment stands.

Expect: `lookup_loan`. Citation `tool:lookup_loan`.

## 2. Payment breakdown (tool only)

> For loan 100245, what are the next three payments and how much of each is escrow?

Expect: `get_payment_schedule`. Citation `tool:get_payment_schedule`.

## 3. Escrow increase + annual analysis policy (POLICY)

> Loan 100245 escrow payment went up — why, and what does annual analysis policy say we tell the borrower?

Expect: `get_escrow_breakdown` + `search_policy`. Policy hit: Annual Analysis
(`DP17-ESC054.v35`). Answer should name +$20.00, effective 2026-06-01, drivers
county tax and hazard insurance.

## 4. Escrow surplus handling (POLICY)

> Loan 100245 has extra funds sitting in escrow after the review — what does our overage policy say we do, and what do I tell Alex?

Expect: `search_policy` (Overages, possibly Annual Analysis) + optional
`get_escrow_breakdown`. Policy citation required.

## 5. Hardship options + loss mitigation policy (POLICY)

> Loan 100245 is current but the borrower says income dropped and they may miss next month — check the account and walk me through the repayment plan options per policy.

Expect: `lookup_loan` or `check_hardship_eligibility` + `search_policy`.
Policy hits: Loss Mitigation — Repayment Plans / Loss Mitigation SOP.

---

## Run one

```powershell
$body = @{
  message    = "Loan 100245 escrow payment went up — why, and what does annual analysis policy say we tell the borrower?"
  session_id = "demo-100245"
  rep_id     = "rep-demo"
} | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:8000/chat" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 300 | Select-Object -ExpandProperty Content
```

Notes:

- Borrower-name search is mock-only; real Loan Services API is loan-id keyed,
  so keep demo prompts anchored on `100245`.
- Policy corpus is the cached Confluence export only — no synthetic SOPs.
