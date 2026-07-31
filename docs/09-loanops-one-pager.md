# LoanOps Agent — One-Pager

**Audience:** Srini  
**Status:** Working demo / internal prototype  
**Owner:** Mohit Bohra  

---

## What it is

**LoanOps** is an **internal, citation-grounded AI copilot for mortgage-servicing care reps**.

A rep asks a borrower question in plain English. The agent:

1. Retrieves relevant **policy / SOP** chunks (with citations)
2. Looks up **loan data** (payments, escrow, schedules, and related facts)
3. Drafts a **rep-ready answer** for the rep to review, approve, or escalate

---

## Who it is for

| User | Need |
|------|------|
| Care rep (Tier 1/2) | Fast, citable answer + draft reply |

---

## Problem → outcome

| Today | With LoanOps |
|-------|----------------|
| Rep hunts SOPs, wiki, loan screens | One ask → cited draft |
| Inconsistent answers, weak audit | Every factual claim cited (`policy:` / `tool:`) |
| High AHT on common Qs | Target: lower AHT, higher FCR |

**Scope:** not locked yet — open to expand based on your direction (which care workflows / loan domains to prioritize first).

---

## How it works (short)

```
Rep UI → Agent API → RAG (SOPs) + Tools API (loan data)
                   → LLM draft → human Approve / Escalate
```

- **Hybrid:** same Python codebase local (Ollama + Qdrant) or cloud (Bedrock + Qdrant Cloud) via env swap
- **Providers:** chat, embeddings, vector store, audit — backends swapped by config
- **Quality gate:** refusal / escalation behaviour plus an eval gate on groundedness and citation coverage

---

Related: [SPMI-1171](https://pennymac.atlassian.net/browse/SPMI-1171) — LoanOps is the **internal care-rep agent-assist** path alongside that servicing AI work.
