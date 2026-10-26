"""Build capability embeddings for merged EAKG (artifact store / file mirror)."""

from __future__ import annotations

from pathlib import Path

import httpx
from rdflib import Graph

from packages.capability_kg.catalog import CapabilityCatalog
from packages.capability_kg.embed_index import (
    EmbeddingEntry,
    EmbedFn,
    build_index,
    save_index,
)
from packages.capability_kg.ontology import DEFAULT_NAMESPACE
from packages.common.providers.factory import get_graph_store
from packages.common.providers.graph_store import named_graph_iri
from packages.common.settings import get_settings
from packages.eakg.artifact_store import get_eakg_artifact_store
from packages.eakg.merge import catalog_from_shards
from packages.eakg.pipeline_layout import postgres_dir, resolve_file_shard_dir
from packages.eakg.runtime import eakg_runtime


async def _construct_named_graph(query_url: str, graph_iri: str, *, auth_token: str = "") -> Graph:
    """SPARQL CONSTRUCT one named graph as Turtle → rdflib Graph."""
    sparql = f"CONSTRUCT {{ ?s ?p ?o }} WHERE {{ GRAPH <{graph_iri}> {{ ?s ?p ?o }} }}"
    headers = {
        "Content-Type": "application/sparql-query",
        "Accept": "text/turtle",
    }
    if auth_token.strip():
        headers["Authorization"] = f"Bearer {auth_token.strip()}"
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(query_url, content=sparql.encode("utf-8"), headers=headers)
        resp.raise_for_status()
    g = Graph()
    if resp.text.strip():
        g.parse(data=resp.text, format="turtle")
    return g


async def catalog_from_graph_store(
    *,
    repository_ids: list[str],
    namespace: str = DEFAULT_NAMESPACE,
    approved_only: bool = False,
    include_cross_app: bool = True,
) -> CapabilityCatalog:
    """Merge live SPARQL named graphs into a CapabilityCatalog."""
    cfg = get_settings()
    query_url = cfg.graph_store.query_url
    token = cfg.graph_store.auth_token
    flat = Graph()
    ids = list(repository_ids)
    if include_cross_app:
        ids = [*ids, "cross_app"]
    for rid in ids:
        iri = named_graph_iri(rid, namespace=namespace)
        part = await _construct_named_graph(query_url, iri, auth_token=token)
        for triple in part:
            flat.add(triple)
    # Touch factory so config errors surface early (auth etc.)
    _ = get_graph_store()
    return CapabilityCatalog(
        flat,
        namespace=namespace,
        approved_only=approved_only,
        semantic=False,
    )


async def _persist_index(
    index: dict[str, EmbeddingEntry], shard_dir: str | Path
) -> Path:
    payload = {
        "version": 1,
        "capabilities": [
            {
                "id": e.id,
                "text": e.text,
                "text_hash": e.text_hash,
                "vector": e.vector,
            }
            for e in sorted(index.values(), key=lambda x: x.id)
        ],
    }
    arts = get_eakg_artifact_store()
    arts.put_embeddings(payload)
    dest = postgres_dir(shard_dir) / "embeddings.json"
    if arts.backend == "file":
        return save_index(dest, index)
    return dest


async def embed_shards(
    shard_dir: str | Path,
    embed: EmbedFn,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    approved_only: bool = False,
) -> Path:
    """Embed capabilities from file mirrors (tests / offline)."""
    caps = catalog_from_shards(
        shard_dir,
        namespace=namespace,
        approved_only=approved_only,
        semantic=False,
    )
    records = caps.list_capabilities(limit=10_000)
    index = await build_index(records, embed)
    return await _persist_index(index, shard_dir)


async def embed_from_settings(embed: EmbedFn) -> Path:
    """Product: embed from live GraphDB when postgres backend; else file shards."""
    cfg = get_settings()
    root = resolve_file_shard_dir(cfg.eakg_store.file_shard_dir)
    if cfg.eakg_store.backend == "postgres":
        registry, _store, _arts = eakg_runtime(cfg)
        ids = [r.repository_id for r in registry.list()]
        caps = await catalog_from_graph_store(
            repository_ids=ids,
            namespace=cfg.capability_kg.namespace,
            approved_only=cfg.capability_kg.approved_only,
        )
        records = caps.list_capabilities(limit=10_000)
        index = await build_index(records, embed)
        return await _persist_index(index, root)
    return await embed_shards(
        root,
        embed,
        namespace=cfg.capability_kg.namespace,
        approved_only=cfg.capability_kg.approved_only,
    )
