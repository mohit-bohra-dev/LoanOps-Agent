# LoanOps overview decks

Written for tech leads and stakeholders **without** code access. Send either file by email or Teams.

| Deck | PowerPoint | PDF |
| --- | --- | --- |
| Long guide | [`LoanOps-Complete-Guide.pptx`](LoanOps-Complete-Guide.pptx) | [`LoanOps-Complete-Guide.pdf`](LoanOps-Complete-Guide.pdf) |
| Short briefing | [`LoanOps-Stakeholder-Briefing-v2.pptx`](LoanOps-Stakeholder-Briefing-v2.pptx) | [`LoanOps-Stakeholder-Briefing-v2.pdf`](LoanOps-Stakeholder-Briefing-v2.pdf) |

The long guide is 66 slides in 7 sections. Each component is WHAT / USE / WHY.

- **A. Why LoanOps exists:** the problem, the goal, what it is and is not, who it is for
- **B. How it is used:** IDE and Chat UI, Eval Portal, one answer step by step, refusals
- **C. Runtime building blocks:** Chat UI, Agent, AI model, the tool room, tools, live API calls, credential broker, swappable providers
- **D. Knowledge:** EAKG, embeddings, ApiIndex, documents, GraphRAG, engineering map, Graphify, stores
- **E. Pipelines:** each job, plus how you start a run, see if it finished, and see if data is fresh
- **F. Safety:** privacy, read-only layers, login today vs person login, citations, quality targets
- **G. Status:** connected apps (Core Components live reads paused), cloud design, gaps, roadmap, glossary, FAQ

The short briefing is 30 slides for a meeting: problem, tool room, knowledge jobs, login, cloud design, and the decisions we want. Term-by-term slides stay in the long guide.

## Regenerate after edits

```powershell
uv run --with python-pptx --with reportlab python presentations/loanops-overview/build_deck.py
```

Slide content lives in the `SLIDES` list in [`build_deck.py`](build_deck.py).
