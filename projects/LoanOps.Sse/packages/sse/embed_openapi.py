"""CLI: build OpenAPI operation embedding sidecar.

Usage:
  uv run python -m packages.sse.embed_openapi
"""

from __future__ import annotations

import asyncio
import sys

from packages.common.providers.factory import get_embedding_provider
from packages.common.settings import get_settings
from packages.sse.loader import DEFAULT_SWAGGER_LINKS, OpenApiCatalogService, resolve_swagger_links
from packages.sse.semantic import (
    OpenApiEmbeddingEntry,
    openapi_embeddings_path,
    operation_text,
    save_openapi_index,
    text_hash,
)


async def _main() -> int:
    cfg = get_settings()
    swagger_links = resolve_swagger_links(cfg.sse.swagger_links, cfg.sse.swagger_urls) or list(
        DEFAULT_SWAGGER_LINKS
    )
    fixture_path = cfg.sse.fixture_path or None
    if cfg.sse.use_fixture and not fixture_path:
        fixture_path = "data/sse-fixture-openapi.json"
    catalog_fixture = fixture_path if (cfg.sse.use_fixture or cfg.sse.fixture_path) else None
    service = OpenApiCatalogService(
        swagger_links=swagger_links,
        api_base_url=cfg.sse.api_base_url,
        bearer_token=cfg.sse.api_key,
        fixture_path=catalog_fixture,
    )
    catalog = await service.load(refresh=True)
    embedder = get_embedding_provider()

    async def embed(text: str) -> list[float]:
        result = await embedder.embed(text)
        return list(result.vector)

    entries: dict[str, OpenApiEmbeddingEntry] = {}
    for op in catalog.operations:
        text = operation_text(op)
        vec = await embed(text)
        entries[op.id] = OpenApiEmbeddingEntry(
            id=op.id,
            text=text,
            text_hash=text_hash(text),
            vector=vec,
        )
    out = openapi_embeddings_path(cfg.eakg.shard_dir)
    save_openapi_index(out, entries)
    print(f"Wrote {len(entries)} OpenAPI embeddings to {out}")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
