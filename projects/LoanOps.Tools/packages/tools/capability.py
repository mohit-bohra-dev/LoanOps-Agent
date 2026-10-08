"""EAKG capability search block for search_sse_apis (D4 shards only)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from packages.tools.capability_catalog import CapabilityCatalogService

CapabilityBlock = Callable[[str, int], Awaitable[str | None]]


def make_eakg_capability_search_block(
    service: CapabilityCatalogService,
) -> CapabilityBlock:
    """Return a capability_block closure bound to a cached catalog service."""

    async def eakg_capability_search_block(query: str, limit: int = 15) -> str | None:
        if not service.enabled:
            return None
        repos = service.shard_dir / "repos"
        if not repos.is_dir() or not any(p.is_dir() for p in repos.iterdir()):
            return None
        caps = service.catalog()
        if caps is None:
            return None
        records = await caps.search_capabilities(query, limit=limit)
        if not records:
            records = await caps.find_capabilities_for_intent(query, limit=limit)
        if not records:
            return None
        lines = ["Capabilities (EAKG):"]
        lines.extend(r.summary_line() for r in records)
        return "\n".join(lines)

    return eakg_capability_search_block


async def eakg_capability_search_block(query: str, limit: int = 15) -> str | None:
    """Default block: builds a one-off service from get_settings (tests / legacy)."""
    from packages.common.settings import get_settings

    settings = get_settings()
    cfg = settings.capability_kg
    if not cfg.enabled:
        return None

    shards = Path(settings.eakg.shard_dir)
    repos = shards / "repos"
    if not repos.is_dir() or not any(p.is_dir() for p in repos.iterdir()):
        return None

    embed_query = None

    async def _embed(text: str) -> list[float]:
        from packages.common.providers.factory import get_embedding_provider

        result = await get_embedding_provider().embed(text)
        return list(result.vector)

    from packages.tools.capability_catalog import use_semantic

    if use_semantic(semantic_flag=cfg.semantic, shard_dir=shards):
        embed_query = _embed

    service = CapabilityCatalogService(
        shards,
        namespace=cfg.namespace,
        approved_only=cfg.approved_only,
        semantic=cfg.semantic,
        embed_query=embed_query,
        enabled=cfg.enabled,
    )
    return await make_eakg_capability_search_block(service)(query, limit)
