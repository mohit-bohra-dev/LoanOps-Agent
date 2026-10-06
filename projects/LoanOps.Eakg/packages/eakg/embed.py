"""Build capability embeddings for merged EAKG shards (offline, after extract)."""

from __future__ import annotations

from pathlib import Path

from packages.capability_kg.embed_index import (
    EmbedFn,
    build_index,
    embeddings_path_for_shards,
    save_index,
)
from packages.capability_kg.ontology import DEFAULT_NAMESPACE
from packages.eakg.merge import catalog_from_shards


async def embed_shards(
    shard_dir: str | Path,
    embed: EmbedFn,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    approved_only: bool = False,
) -> Path:
    """Embed all capabilities in shards. Run after onboard / cross-app."""
    caps = catalog_from_shards(
        shard_dir,
        namespace=namespace,
        approved_only=approved_only,
        semantic=False,
    )
    records = caps.list_capabilities(limit=10_000)
    index = await build_index(records, embed)
    dest = embeddings_path_for_shards(shard_dir)
    return save_index(dest, index)
