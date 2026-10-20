# capability_kg data (legacy path)

**Product discovery uses EAKG** (`data/eakg` shards) — D4.

The single-file OpenAPI build CLI (`packages.capability_kg.build`) is
**removed**. Shared library code under `packages/capability_kg/` (catalog,
ontology, SPARQL, embed index) still backs EAKG merge/search.

Rebuild enterprise knowledge via:

```powershell
uv run python -m packages.eakg onboard --id <repo>
uv run python -m packages.eakg cross-app
```

See `docs/EAKG_COMMITTED_VS_LOCAL.md`.
