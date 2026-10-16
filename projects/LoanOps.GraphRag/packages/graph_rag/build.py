"""Offline GraphRAG build: P4 communities; optional P5 LLM extract."""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
from typing import Any

from packages.common.providers.factory import (
    get_chat_provider,
    get_embedding_provider,
    get_vector_store_provider,
)
from packages.common.settings import get_settings
from packages.docs.service import build_chunk_metadata, relative_corpus_path
from packages.graph_rag.artifact import refuse_confluence_repo_write, write_artifact
from packages.graph_rag.communities import (
    SUMMARIES_NAMESPACE,
    build_community_records,
    corpus_hash,
    load_doc_links,
)
from packages.graph_rag.extract import extract_chunk
from packages.graph_rag.graph_merge import merge_doc_and_entity_edges, resolve_entities
from packages.graph_rag.schema import PROMPT_VERSION, SCHEMA_VERSION
from packages.rag.chunker import MarkdownChunker
from packages.common.providers.vector_store import VectorDocument

logger = logging.getLogger(__name__)


def _resolved_model_id() -> str:
    cfg = get_settings()
    if cfg.llm.provider == "bedrock":
        return cfg.llm.bedrock.model_id
    if cfg.llm.provider == "ollama":
        return cfg.llm.ollama.model_accurate or cfg.llm.ollama.model_fast
    if cfg.llm.provider == "openai" and cfg.llm.openai is not None:
        return cfg.llm.openai.model
    if cfg.llm.provider == "gemini":
        gem = cfg.llm.gemini
        return gem.model if gem is not None else "gemini"
    if cfg.llm.provider == "aoai" and cfg.llm.aoai is not None:
        return cfg.llm.aoai.deployment_accurate
    return cfg.llm.provider


def _chunk_corpus(corpus_root: Path) -> list[tuple[str, str, str]]:
    """Return list of (chunk_id, rel_path, content)."""
    chunker = MarkdownChunker()
    out: list[tuple[str, str, str]] = []
    root = corpus_root.resolve()
    for path in sorted(root.rglob("*.md")):
        if any(part.startswith("_") for part in path.parts):
            continue
        rel = relative_corpus_path(path, root)
        text = path.read_text(encoding="utf-8")
        meta = build_chunk_metadata(corpus="sop", rel_path=rel)
        for ch in chunker.chunk(text, metadata=meta):
            out.append((ch.chunk_id, rel, ch.content))
    return out


async def _run_extract(
    *,
    corpus_root: Path,
    cache_dir: Path,
    model_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], int, int]:
    chat = get_chat_provider()
    chunks = _chunk_corpus(corpus_root)
    per_chunk: list[tuple[str, str, list[dict[str, Any]], list[dict[str, Any]]]] = []
    gap_rows: list[dict[str, Any]] = []
    hits = 0
    calls = 0
    for chunk_id, path, content in chunks:
        ents, rels, gaps, cache_hit = await extract_chunk(
            chunk_id=chunk_id,
            path=path,
            content=content,
            model_id=model_id,
            chat=chat,
            cache_dir=cache_dir,
        )
        if cache_hit:
            hits += 1
        else:
            calls += 1
        per_chunk.append((chunk_id, path, ents, rels))
        gap_rows.extend(g.to_dict() for g in gaps)
    graph = resolve_entities(per_chunk)
    return graph, gap_rows, hits, calls


def _assert_model_pin(artifact_dir: Path, model_id: str, *, rebuild: bool) -> None:
    manifest_path = artifact_dir / "manifest.json"
    if not manifest_path.is_file() or rebuild:
        return
    try:
        import json

        prev = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(prev, dict):
        return
    old = str(prev.get("model_id") or "")
    if old and old != model_id:
        raise SystemExit(
            f"refuse: manifest model_id={old!r} != current {model_id!r}; "
            "pass --rebuild to overwrite"
        )


async def build_and_index(
    *,
    doc_links_path: Path,
    corpus_root: Path,
    artifact_dir: Path,
    extract: bool = False,
    write_repo_artifact: bool = True,
    rebuild: bool = False,
) -> int:
    cfg = get_settings()
    refuse_confluence_repo_write(
        sop_source=cfg.data.sop_source,
        write_repo_artifact=write_repo_artifact,
    )

    edges = load_doc_links(doc_links_path)
    graph_payload: dict[str, Any] | None = None
    gap_ledger: list[dict[str, Any]] | None = None
    model_id: str | None = None
    phase = "p4"
    prompt_version: str | None = None
    schema_version: str | None = None

    if extract:
        model_id = _resolved_model_id()
        _assert_model_pin(artifact_dir, model_id, rebuild=rebuild)
        cache_dir = artifact_dir / "cache"
        graph_payload, gap_ledger, hits, calls = await _run_extract(
            corpus_root=corpus_root,
            cache_dir=cache_dir,
            model_id=model_id,
        )
        logger.info("Extract done: cache_hits=%s llm_calls=%s", hits, calls)
        edges = merge_doc_and_entity_edges(edges, list(graph_payload.get("path_edges") or []))
        phase = "p5"
        prompt_version = PROMPT_VERSION
        schema_version = SCHEMA_VERSION

    records = build_community_records(edges, corpus_root)
    c_hash = corpus_hash(corpus_root)
    write_artifact(
        artifact_dir,
        communities=records,
        corpus_hash=c_hash,
        graph=graph_payload,
        model_id=model_id,
        prompt_version=prompt_version,
        schema_version=schema_version,
        phase=phase,
        summary_kind="extractive",
        gap_ledger=gap_ledger,
    )
    logger.info("Wrote %s communities → %s (phase=%s)", len(records), artifact_dir, phase)

    embedder = get_embedding_provider()
    store = get_vector_store_provider()
    dims = await embedder.get_dimensions()
    await store.create_collection(SUMMARIES_NAMESPACE, vector_size=dims)

    for rec in records:
        emb = await embedder.embed(str(rec["summary"]))
        doc = VectorDocument(
            id=str(rec["id"]),
            embedding=emb.vector,
            metadata={
                "community_id": rec["id"],
                "member_paths": rec["member_paths"],
                "corpus": "graphrag_summary",
            },
            text=str(rec["summary"]),
        )
        await store.upsert([doc], namespace=SUMMARIES_NAMESPACE)

    logger.info("Indexed %s summaries into ns=%s", len(records), SUMMARIES_NAMESPACE)
    return len(records)


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Build GraphRAG communities (+ optional P5 extract)")
    parser.add_argument("--doc-links", type=Path, default=Path("data/docs/doc_links.json"))
    parser.add_argument("--corpus", type=Path, default=Path("data/sops"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("data/graphrag"))
    parser.add_argument(
        "--extract",
        action="store_true",
        help="P5: LLM entity/relation extract with cache (uses LLM__*)",
    )
    parser.add_argument(
        "--write-repo-artifact",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write data/graphrag into repo (refused when DATA__SOP_SOURCE != local)",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Allow overwriting artifact when model_id differs from manifest",
    )
    args = parser.parse_args()
    n = asyncio.run(
        build_and_index(
            doc_links_path=args.doc_links,
            corpus_root=args.corpus,
            artifact_dir=args.artifact_dir,
            extract=args.extract,
            write_repo_artifact=args.write_repo_artifact,
            rebuild=args.rebuild,
        )
    )
    print(f"built {n} communities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
