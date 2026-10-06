# LoanOps Agent — One-Pager

**Audience:** Stakeholders / demos  
**Status:** Working demo / internal prototype  
**Owner:** Mohit Bohra  

---

## What it is

**LoanOps** is an **internal, citation-grounded AI platform** for enterprise teams — not locked to one job title.

Anyone internal can ask in plain English. The agent:

1. Discovers the right **APIs / capabilities** (EAKG + OpenAPI via MCP)
2. Searches **docs / SOPs** (with citations)
3. Calls **read-oriented tools** and drafts a **grounded answer** for human review

It is **not** a public borrower chatbot. Mutating business actions stay out of v1 tool policy unless explicitly approved later.

---

## Who it is for

| User | Need |
|------|------|
| Engineer / analyst | Find and call the right API; impact / capability questions |
| PM / ops | Docs + Jira/wiki context (wiki tools when ported); grounded drafts |
| Any internal role | Same MCP surface; scopes differ by `AGENT_ROLE` |

---

## Problem → outcome

| Today | With LoanOps |
|-------|----------------|
| Hunt swagger, wiki, repo docs, many UIs | One ask → cited answer + tool trace |
| “Which API?” tribal knowledge | EAKG + semantic capability search |
| Weak audit of what was used | Citations (`policy:` / `tool:`) + audit log |

**Scope:** platform for general internal use (ADR-021). Domain content today is mortgage-servicing APIs/docs; the product shape is role-agnostic.

---

## How it works (short)

```
Chat UI / Cursor → Agent API or MCP :8001
                 → search_sse_apis / EAKG / search_docs
                 → call_sse_api → grounded draft
```

- **Hybrid:** same Python codebase local (Ollama + Qdrant) or cloud (Bedrock + Qdrant Cloud) via env swap
- **Providers:** chat, embeddings, vector store, audit — backends swapped by config
- **Quality gate:** refusal / escalation behaviour plus an eval gate on groundedness and citation coverage

---

## Links

- ADR-021 (audience): `decisions.md`
- PRD (historical care-rep framing): `docs/PRD.md`
- Demo pitch: `presentations/demo-pitch/slides.md`
