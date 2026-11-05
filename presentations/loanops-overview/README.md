# LoanOps Complete Guide

One deck, two formats. Written for tech leads and stakeholders **without** code access. You can send either file by email or Teams.

| Format | File |
| --- | --- |
| PowerPoint | [`LoanOps-Complete-Guide.pptx`](LoanOps-Complete-Guide.pptx) |
| PDF | [`LoanOps-Complete-Guide.pdf`](LoanOps-Complete-Guide.pdf) |

65 slides in 7 sections:

- **A. Why LoanOps exists:** the problem, the goal, what it is and is not, who it is for
- **B. How it is used:** the two clients, why the Chat UI exists, example questions, one answer step by step, refusals
- **C. Runtime building blocks:** Chat UI, Agent, AI model, the MCP tool room, tools, live API calls, credential broker, swappable providers
- **D. Knowledge:** EAKG, embeddings, capability embeddings, ApiIndex, document embeddings, GraphRAG, engineering map, Graphify, stores, product vs test mode
- **E. Pipelines:** each one with its source, output, an example, and why it exists
- **F. Safety, security, quality:** privacy, read-only layers, auth, citations and audit, quality targets
- **G. Status and reference:** connected apps, status, gaps, roadmap, recommended decisions, glossary, FAQ

Each component is explained as WHAT / USE / WHY.

## Regenerate after edits

```powershell
uv run --with python-pptx --with reportlab python presentations/loanops-overview/build_deck.py
```

Slide content lives in the `SLIDES` list in [`build_deck.py`](build_deck.py).
