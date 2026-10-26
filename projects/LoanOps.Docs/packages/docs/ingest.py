"""CLI: index SOP markdown into docs vector namespace (pgvector).

Product: live Confluence via policy provider (``DATA__SOP_CONFLUENCE_MODE=live``).
File/offline: directory arg or ``Postgres/sop_page_cache``.

Usage:
  uv run python -m packages.docs.ingest
  uv run python -m packages.docs.ingest path/to/markdown
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from packages.common.providers.factory import (
    get_embedding_provider,
    get_policy_source_provider,
    get_vector_store_provider,
)
from packages.common.settings import get_settings
from packages.docs.service import DocsService

logger = logging.getLogger(__name__)


async def ingest_sops(sops_dir: str | Path) -> int:
    """Index ``*.md`` under ``sops_dir`` into the ``docs`` vector namespace."""
    root = Path(sops_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"SOP directory not found: {root}")
    svc = DocsService(get_embedding_provider(), get_vector_store_provider())
    await svc.ensure_collection()
    count = await svc.index_directory(root, corpus="sop")
    logger.info("Indexed %s chunks from %s (namespace=docs).", count, root)
    return count


async def ingest_from_policy_provider() -> int:
    """Fetch SOPs via configured policy source and embed into pgvector ``docs``."""
    pages = await get_policy_source_provider().fetch_pages()
    svc = DocsService(get_embedding_provider(), get_vector_store_provider())
    await svc.ensure_collection()
    try:
        from packages.eakg.artifact_store import get_eakg_artifact_store

        arts = get_eakg_artifact_store()
    except Exception:  # noqa: BLE001
        arts = None

    total = 0
    for page in pages:
        rel = str(page.metadata.get("source") or page.source or page.title)
        if not rel.endswith(".md"):
            rel = f"{rel}.md" if "/" in rel else f"confluence/{rel}.md"
        rel_path = (
            rel.replace("confluence/", "", 1) if rel.startswith("confluence/") else rel
        )
        if arts is not None:
            arts.put_sop_page(rel_path, page.content)
        total += await svc.index_markdown_text(
            page.content,
            rel_path=rel_path,
            corpus="sop",
            extra_metadata={
                "title": page.title,
                **{k: v for k, v in page.metadata.items() if isinstance(v, str)},
            },
        )
    logger.info("Indexed %s chunks from %s policy page(s).", total, len(pages))
    return total


async def ingest_default() -> int:
    """Product live Confluence when configured; else file-mode SOP cache."""
    cfg = get_settings()
    if cfg.data.sop_confluence_mode == "live" or cfg.data.sop_source in (
        "confluence",
        "both",
    ):
        if cfg.data.sop_confluence_mode == "live" or cfg.data.sop_source != "local":
            return await ingest_from_policy_provider()
    cache = Path(cfg.data.confluence.artifact_dir)
    if cache.is_dir():
        return await ingest_sops(cache)
    raise FileNotFoundError(
        "No SOP corpus: set DATA__SOP_CONFLUENCE_MODE=live or pass a markdown directory"
    )


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        description="Ingest SOP markdown into the docs vector namespace"
    )
    parser.add_argument(
        "sops_dir",
        nargs="?",
        default="",
        help="Optional directory of SOP markdown (default: policy provider / cache)",
    )
    args = parser.parse_args(argv)
    try:
        if args.sops_dir:
            asyncio.run(ingest_sops(args.sops_dir))
        else:
            asyncio.run(ingest_default())
    except Exception as e:
        logger.exception("Ingestion failed: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
