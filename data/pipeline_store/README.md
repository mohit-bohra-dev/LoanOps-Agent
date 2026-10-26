# File-mode pipeline store

Offline / test mirror of product stores. **Not product truth.**

| Folder | Mirrors |
|---|---|
| `GraphDb/named_graphs/` | SPARQL named graphs (Turtle) |
| `Postgres/` | EAKG artifact tables (registry, interface, ops, embeddings, …) |
| `Pgvector/` | Optional offline vector sidecars |

Product: `EAKG_STORE__BACKEND=postgres` + live GraphDB + Postgres + pgvector — **no** writes here.

Tests: set `EAKG_STORE__FILE_SHARD_DIR` to a temp dir (same layout).
