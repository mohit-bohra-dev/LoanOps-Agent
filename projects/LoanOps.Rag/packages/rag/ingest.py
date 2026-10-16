from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from packages.common.providers.factory import (
    get_embedding_provider,
    get_policy_source_provider,
    get_vector_store_provider,
)
from packages.rag.chunker import MarkdownChunker
from packages.common.providers.vector_store import VectorDocument

logger = logging.getLogger(__name__)

# Same namespace DocsService / search_docs reads (doc-graphrag P1).
DOCS_NAMESPACE = "docs"


def _normalize_rel_path(raw: str) -> str:
    rel = raw.replace("\\", "/").lstrip("./")
    if rel.startswith("data/sops/"):
        rel = rel[len("data/sops/") :]
    return rel


def _chunk_meta(rel_path: str, page_meta: dict[str, Any]) -> dict[str, Any]:
    """Frozen metadata schema aligned with DocsService.build_chunk_metadata."""
    parts = rel_path.split("/")
    category = str(page_meta.get("category") or (parts[0] if len(parts) > 1 else ""))
    state = str(page_meta.get("state") or "")
    if not state and parts and parts[0] == "state-specific" and len(parts) > 1:
        stem = parts[-1].removesuffix(".md")
        state = stem.replace("-policy", "").replace("_", "-")
    meta: dict[str, Any] = {
        "corpus": "sop",
        "path": rel_path,
        "category": category,
        "state": state,
        "heading_path": str(page_meta.get("heading_path") or ""),
    }
    for k, v in page_meta.items():
        if k not in meta and k not in ("path", "source"):
            meta[k] = v
    return meta


async def ingest_sops(sops_dir: str | Path) -> None:
    """
    Reads SOPs from provider, chunks them, embeds them, and stores them in the
    vector store under the ``docs`` namespace (same target as ``DocsService`` /
    ``search_docs``).
    """
    _ = sops_dir  # CLI positional retained; source of truth is policy provider
    chunker = MarkdownChunker()
    embedder = get_embedding_provider()
    vector_store = get_vector_store_provider()
    policy_provider = get_policy_source_provider()

    pages = await policy_provider.fetch_pages()
    logger.info("Fetched %s policy pages for ingestion.", len(pages))

    try:
        dims = await embedder.get_dimensions()
        await vector_store.create_collection(DOCS_NAMESPACE, vector_size=dims)
        logger.info("Created collection/namespace %r.", DOCS_NAMESPACE)
    except Exception as e:
        logger.info("Collection %r may already exist or error occurred: %s", DOCS_NAMESPACE, e)

    for page in pages:
        logger.info("Ingesting %s...", page.title)
        raw_meta = dict(page.metadata)
        rel = _normalize_rel_path(
            str(raw_meta.get("source") or raw_meta.get("path") or page.title)
        )
        meta = _chunk_meta(rel, raw_meta)
        chunks = chunker.chunk(page.content, metadata=meta)

        for chunk in chunks:
            embedding_res = await embedder.embed(chunk.content)
            doc = VectorDocument(
                id=chunk.chunk_id,
                embedding=embedding_res.vector,
                metadata=chunk.metadata,
                text=chunk.content,
            )
            await vector_store.upsert([doc], namespace=DOCS_NAMESPACE)

    logger.info("Ingestion complete (namespace=%s).", DOCS_NAMESPACE)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Ingest SOPs into Vector Store (docs ns)")
    parser.add_argument("sops_dir", help="Directory containing SOP markdown files")
    args = parser.parse_args()

    try:
        import asyncio

        asyncio.run(ingest_sops(args.sops_dir))
    except Exception as e:
        logger.exception("Ingestion failed: %s", e)
