# capability_kg data (legacy path)

**Product discovery uses EAKG** (`data/eakg` shards) — D4.

This directory may hold experimental Turtle from
`python -m packages.capability_kg.build`. It is **not** read by
`search_sse_apis` / MCP agent discovery anymore.

Rebuild enterprise knowledge via:

```powershell
uv run python -m packages.eakg onboard --id <repo>
uv run python -m packages.eakg cross-app
```

See `docs/EAKG_COMMITTED_VS_LOCAL.md`.
