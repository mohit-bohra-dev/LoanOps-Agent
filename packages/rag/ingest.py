from __future__ import annotations

import logging
from pathlib import Path

from packages.common.providers.factory import get_embedding_provider, get_vector_store_provider
from packages.rag.chunker import MarkdownChunker

logger = logging.getLogger(__name__)


async def ingest_sops(sops_dir: str | Path) -> None:
    """
    Reads SOPs from directory, chunks them, embeds them, and stores them in the vector store.
    """
    sops_path = Path(sops_dir)
    if not sops_path.exists():
        raise FileNotFoundError(f"SOPs directory not found: {sops_dir}")

    chunker = MarkdownChunker()
    embedder = get_embedding_provider()
    vector_store = get_vector_store_provider()

    # Find all markdown files
    md_files = list(sops_path.glob("**/*.md"))
    logger.info(f"Found {len(md_files)} SOP files for ingestion.")

    # Ensure collection exists
    try:
        dims = await embedder.get_dimensions()
        await vector_store.create_collection("sops", vector_size=dims)
        logger.info("Created collection 'sops'.")
    except Exception as e:
        # It might already exist, which is fine in some providers or handled by them
        logger.info(f"Collection 'sops' may already exist or error occurred: {e}")

    for file_path in md_files:
        logger.info(f"Ingesting {file_path.name}...")
        text = file_path.read_text(encoding="utf-8")

        # Extract YAML frontmatter if present
        content = text
        metadata = {"source": str(file_path.relative_to(sops_path))}
        if text.startswith("---"):
            try:
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    # Simple YAML-like split for frontmatter
                    frontmatter = parts[1]
                    content = parts[2].strip()
                    for line in frontmatter.splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            metadata[k.strip()] = v.strip()
            except Exception as e:
                logger.warning(f"Failed to parse frontmatter in {file_path.name}: {e}")

        chunks = chunker.chunk(content, metadata=metadata)

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
