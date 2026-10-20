"""CLI: index local SOP markdown via DocsService (single docs writer).

Usage:
  uv run python -m packages.docs.ingest data/sops
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from packages.common.providers.factory import (
    get_embedding_provider,
    get_vector_store_provider,
)
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


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        description="Ingest local SOP markdown into the docs vector namespace"
    )
    parser.add_argument("sops_dir", help="Directory containing SOP markdown files")
    args = parser.parse_args(argv)
    try:
        asyncio.run(ingest_sops(args.sops_dir))
    except Exception as e:
        logger.exception("Ingestion failed: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
