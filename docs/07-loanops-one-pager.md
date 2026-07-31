# LoanOps Agent — One-Pager

**Audience:** Srini (demo prep)  
**Status:** Working demo / internal prototype  
**Owner:** Mohit Bohra  
**Related:** [Servicing Confluence](https://pennymac.atlassian.net/wiki/spaces/SC/overview?homepageId=1777369156)

---

## What it is

**LoanOps** is an **internal, citation-grounded AI copilot for mortgage-servicing care reps**.

A rep asks a borrower question in plain English. The agent:

1. Retrieves relevant **policy / SOP** chunks (with citations)
2. Looks up **read-only loan data** (payments, escrow, schedules, etc.)
3. Drafts a **rep-ready answer** for human approve / escalate

It is **not borrower-facing**. It does **not** post payments, start plans, or place holds.

---

## Who it is for

| User | Need |
|------|------|
| Care rep (Tier 1/2) | Fast, citable answer + draft reply |
| Supervisor | Escalation / QA sampling |
| Compliance | Audit trail of prompts, retrieval, tools, outputs |

---

## Problem → outcome

| Today | With LoanOps |
|-------|----------------|
| Rep hunts SOPs, wiki, loan screens | One ask → cited draft |
| Inconsistent answers, weak audit | Every factual claim cited (`policy:` / `tool:`) |
| High AHT on common Qs | Target: lower AHT, higher FCR |

**In-scope v1:** payment summary / due dates / late fees, escrow, hardship program info (eligibility hints only), payoff *informational* (not a quote), policy/SOP search, draft reply.

**Out of scope v1:** borrower chat/voice, rate quotes, mutating actions, fair-lending decisioning, licensed legal/tax/financial advice.

---

## How it works (short)

```
Rep UI → Agent API → RAG (SOPs) + Tools API (loan data, read-only)
                   → LLM draft → safety check → human Approve / Escalate
```

- **Hybrid:** same Python codebase local (Ollama + Qdrant) or cloud (Bedrock + Qdrant Cloud) via env swap
- **Providers:** chat, embeddings, vector store, PII, safety, audit — no hard-coded vendor in app code
- **Guardrails:** PII handling, content safety, refusal/escalation, eval gate (groundedness + citation coverage)

---

## Where it fits

Servicing already has an approved agentic-AI intake — [SSI-589](https://pennymac.atlassian.net/browse/SSI-589) (Collections / Loss Mitigation) and initiative [SPMI-1171](https://pennymac.atlassian.net/browse/SPMI-1171), targeting **borrower-facing voice (AIVA) + web** for call deflection and payment capture.

LoanOps is the **other half of that picture**: it assists the **live agent** rather than replacing the call.

| | **LoanOps (this)** | **SSI-589 / SPMI-1171** |
|---|--------------------|--------------------------|
| Facing | Internal rep | Borrower |
| Channel | Rep UI | Voice + web self-service |
| Action model | Read-only, human approves | Automated handling, payments, escalation |
| Primary metric | AHT / FCR / groundedness | Call deflection, containment, payment capture |

Shared foundation both need: retrieval over servicing policy, read-only loan data access, safety and audit, and evaluation. LoanOps is a working prototype of that layer — it does **not** deliver the SSI-589 scope on its own.

---

## Demo ask

Show one care-rep turn: loan-id question → cited policy + live/mock loan facts → draft for approve. Emphasize **human-in-the-loop** and **read-only** tools.

---

## Links

- PRD: `docs/PRD.md`
- Demo pitch: `presentations/demo-pitch/slides.md`
- Demo queries: `docs/06-demo-queries-100245.md`
