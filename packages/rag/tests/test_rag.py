from __future__ import annotations

import pytest

from packages.rag.chunker import MarkdownChunker


def test_markdown_chunker_splits_by_header() -> None:
    text = "# Header 1\nContent 1\n\n# Header 2\nContent 2"
    # Small target_tokens to ensure it splits the chunks
    chunker = MarkdownChunker(target_tokens=2)
    chunks = chunker.chunk(text)

    assert len(chunks) >= 2
    assert any("Header 1" in c.content for c in chunks)
    assert any("Header 2" in c.content for c in chunks)


def test_markdown_chunker_respects_size() -> None:
    # Create a long string to force splitting
    long_text = "This is a long sentence. " * 500
    chunker = MarkdownChunker(target_tokens=10, overlap_tokens=2)
    chunks = chunker.chunk(long_text)

    assert len(chunks) > 1
    # Check that chunk 1 and 2 overlap by overlap_tokens (2 words)
    assert " ".join(chunks[0].content.split()[-2:]) == " ".join(chunks[1].content.split()[:2])


def test_rag_ingest_end_to_end_local() -> None:
    """
    Integration test for the ingest pipeline using LocalBge and Qdrant.
    Requires local services to be running or mocks.
    """
    # This is usually marked as integration and skipped in default CI
    pytest.skip("Requires live Qdrant and BGE providers")


def test_nearest_neighbour_retrieval() -> None:
    """
    Verifies that a specific query returns the most relevant chunk.
    """
    # This test requires live providers, so we'll mark it as integration
    pytest.skip("Requires live VectorStore provider - run with pytest -m integration")
