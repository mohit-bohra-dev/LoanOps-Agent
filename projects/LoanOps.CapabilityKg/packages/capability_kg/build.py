"""CLI: build capability Turtle from OpenAPI fixture / catalog.

Usage:
  python -m packages.capability_kg.build
  python -m packages.capability_kg.build --fixture data/sse-loanservices-catalog.json
  python -m packages.capability_kg.build --embed
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from packages.capability_kg.catalog import CapabilityCatalog
from packages.capability_kg.embed_index import (
    build_index,
    embeddings_path_for_ttl,
    save_index,
)
from packages.capability_kg.extract_openapi import build_graph_from_openapi_dict
from packages.capability_kg.store import save_graph
from packages.common.settings import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build RDF capability graph from OpenAPI")
    parser.add_argument(
        "--fixture",
        type=str,
        default="",
        help="Path to OpenAPI JSON (default: SSE__FIXTURE_PATH or data/sse-loanservices-catalog.json)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="",
        help="Output Turtle path (default: CAPABILITY_KG__TTL_PATH)",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Also write embeddings.json via get_embedding_provider() (optional; not for CI)",
    )
    args = parser.parse_args(argv)
    cfg = Settings()
    fixture = args.fixture or cfg.sse.fixture_path or "data/sse-loanservices-catalog.json"
    out = args.out or cfg.capability_kg.ttl_path
    path = Path(fixture)
    if not path.is_file():
        print(f"fixture not found: {path}")
        return 1
    raw = json.loads(path.read_text(encoding="utf-8"))
    source_id = "loanservices"
    source_label = "LoanServices"
    if cfg.sse.swagger_links:
        source_id = cfg.sse.swagger_links[0].id
        source_label = cfg.sse.swagger_links[0].label
    graph = build_graph_from_openapi_dict(
        raw,
        source_id=source_id,
        source_label=source_label,
        source_base_url=cfg.sse.api_base_url,
        namespace=cfg.capability_kg.namespace,
    )
    dest = save_graph(graph, out)
    print(f"wrote {dest} triples={len(graph)}")

    if args.embed:
        return asyncio.run(_write_embeddings(Path(out), cfg.capability_kg.namespace))
    return 0


async def _write_embeddings(ttl: Path, namespace: str) -> int:
    from packages.common.providers.factory import get_embedding_provider

    catalog = CapabilityCatalog.from_ttl(ttl, namespace=namespace)
    records = catalog.list_capabilities(limit=500)
    provider = get_embedding_provider()

    async def _embed(text: str) -> list[float]:
        result = await provider.embed(text)
        return list(result.vector)

    entries = await build_index(records, _embed)
    side = embeddings_path_for_ttl(ttl)
    save_index(side, entries)
    print(f"wrote {side} capabilities={len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
