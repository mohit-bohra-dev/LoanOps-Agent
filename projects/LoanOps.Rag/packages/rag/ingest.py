from __future__ import annotations

import logging
from pathlib import Path

from packages.common.providers.factory import (
    get_embedding_provider,
    get_policy_source_provider,
    get_vector_store_provider,
)
from packages.rag.chunker import MarkdownChunker

logger = logging.getLogger(__name__)


async def ingest_sops(sops_dir: str | Path) -> None:
    """
    Reads SOPs from provider, chunks them, embeds them, and stores them in the vector store.
    """
    chunker = MarkdownChunker()
    embedder = get_embedding_provider()
    vector_store = get_vector_store_provider()
    policy_provider = get_policy_source_provider()

    # Fetch pages from the configured provider
    pages = await policy_provider.fetch_pages()
    logger.info(f"Fetched {len(pages)} policy pages for ingestion.")

    # Ensure collection exists
    try:
        dims = await embedder.get_dimensions()
        await vector_store.create_collection("sops", vector_size=dims)
        logger.info("Created collection 'sops'.")
    except Exception as e:
        # It might already exist, which is fine in some providers or handled by them
        logger.info(f"Collection 'sops' may already exist or error occurred: {e}")

    for page in pages:
        logger.info(f"Ingesting {page.title}...")
        chunks = chunker.chunk(page.content, metadata=page.metadata)

        # Process chunks in batches for efficiency
        for chunk in chunks:
            # The VectorDocument typically expects content and embedding
            # We use the provider to embed the content
            embedding_res = await embedder.embed(chunk.content)
            embedding = embedding_res.vector

            # In provider_contracts, VectorDocument usually has content, embedding, and metadata
            from provider_contracts.vector_store import VectorDocument

            doc = VectorDocument(
                id=chunk.chunk_id, embedding=embedding, metadata=chunk.metadata, text=chunk.content
            )
            await vector_store.upsert([doc])

    logger.info("Ingestion complete.")


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Ingest SOPs into Vector Store")
    parser.add_argument("sops_dir", help="Directory containing SOP markdown files")
    args = parser.parse_args()

    try:
        import asyncio

        asyncio.run(ingest_sops(args.sops_dir))
    except Exception as e:
        logger.exception(f"Ingestion failed: {e}")
