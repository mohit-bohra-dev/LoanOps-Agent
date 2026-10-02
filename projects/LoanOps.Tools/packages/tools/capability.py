"""EAKG capability search block for search_sse_apis (D4 shards only)."""

from __future__ import annotations

from pathlib import Path


async def eakg_capability_search_block(query: str, limit: int = 15) -> str | None:
    """Return EAKG shard hits for a query, or None when disabled/empty."""
    from packages.common.settings import Settings

    settings = Settings()
    cfg = settings.capability_kg
    if not cfg.enabled:
        return None

    shards = Path(settings.eakg.shard_dir)
    repos = shards / "repos"
    if not repos.is_dir() or not any(p.is_dir() for p in repos.iterdir()):
        return None

    embed_query = None
    if cfg.semantic:

        async def _embed(text: str) -> list[float]:
            from packages.common.providers.factory import get_embedding_provider

            result = await get_embedding_provider().embed(text)
            return list(result.vector)

        embed_query = _embed

    from packages.eakg.merge import catalog_from_shards

    caps = catalog_from_shards(
        shards,
        namespace=cfg.namespace,
        approved_only=cfg.approved_only,
        semantic=cfg.semantic,
        embed_query=embed_query,
    )
    records = await caps.search_capabilities(query, limit=limit)
    if not records:
        records = await caps.find_capabilities_for_intent(query, limit=limit)
    if not records:
        return None
    lines = ["Capabilities (EAKG):"]
    lines.extend(r.summary_line() for r in records)
    return "\n".join(lines)
