"""Path normalisation / frozen metadata (doc-graphrag P1)."""

from __future__ import annotations

from pathlib import Path

from packages.docs.service import build_chunk_metadata, relative_corpus_path
from packages.rag.chunker import MarkdownChunker


def test_relative_corpus_path_stable_across_roots(tmp_path: Path) -> None:
    root_a = tmp_path / "checkout_a" / "data" / "sops"
    root_b = tmp_path / "checkout_b" / "data" / "sops"
    (root_a / "hardship").mkdir(parents=True)
    (root_b / "hardship").mkdir(parents=True)
    file_a = root_a / "hardship" / "forbearance.md"
    file_b = root_b / "hardship" / "forbearance.md"
    file_a.write_text("# Hi\n", encoding="utf-8")
    file_b.write_text("# Hi\n", encoding="utf-8")

    assert relative_corpus_path(file_a, root_a) == "hardship/forbearance.md"
    assert relative_corpus_path(file_b, root_b) == "hardship/forbearance.md"


def test_chunk_id_identical_for_same_relative_meta() -> None:
    content = "# Forbearance\n\nPause payments when eligible.\n"
    meta_a = build_chunk_metadata(corpus="sop", rel_path="hardship/forbearance.md")
    meta_b = build_chunk_metadata(corpus="sop", rel_path="hardship/forbearance.md")
    chunker = MarkdownChunker()
    a = chunker.chunk(content, meta_a)
    b = chunker.chunk(content, meta_b)
    assert len(a) == 1 and len(b) == 1
    assert a[0].chunk_id == b[0].chunk_id


def test_state_inferred_from_state_specific_path() -> None:
    meta = build_chunk_metadata(corpus="sop", rel_path="state-specific/florida-policy.md")
    assert meta["category"] == "state-specific"
    assert meta["state"] == "florida"
    assert meta["path"] == "state-specific/florida-policy.md"
    assert "heading_path" in meta
