# SOPs

**Product corpus:** Confluence cache only — `data/sops/_confluence/` (gitignored).

Synthetic local SOPs under category folders (`escrow/`, `payments/`, …) were
removed. Ingest and GraphRAG should target `_confluence`.

| Setting | Meaning |
|---|---|
| `DATA__SOP_SOURCE=confluence` | Policy provider reads Confluence (cache or live) |
| `DATA__SOP_CONFLUENCE_MODE=cache` | Read `_confluence` offline |
| `DATA__SOP_CONFLUENCE_MODE=live` | Fetch Confluence REST and refresh `_confluence` |

Seed / refresh cache via live Confluence config in `.env` (see `.env.example`).
