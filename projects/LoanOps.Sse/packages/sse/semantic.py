"""Embed OpenAPI operations for search_sse_apis (sidecar + in-process cache)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packages.sse.catalog import search_operations
from packages.sse.types import ApiOperation

EmbedFn = Callable[[str], Awaitable[list[float]]]

_SKIP_PATH_SEGS = frozenset({"api", "v1", "v2", "v3", "v4", "internal", "external"})
_EMBED_CONCURRENCY = 8


@dataclass(frozen=True)
class OpenApiEmbeddingEntry:
    id: str
    text: str
    text_hash: str
    vector: list[float]


def _split_ident(name: str) -> str:
    s = name.replace("_", " ").replace("-", " ")
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1 \2", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)
    return " ".join(s.split())


def operation_text(op: ApiOperation) -> str:
    """Same idea as EAKG capability_text: summary + path phrases for embedding."""
    chunks: list[str] = [f"{op.method} {op.path}"]
    if op.operation_id:
        chunks.append(_split_ident(op.operation_id))
    if op.summary:
        chunks.append(op.summary.strip())
    if op.description:
        chunks.append(op.description.strip())
    for seg in op.path.strip("/").split("/"):
        if not seg or seg.startswith("{") or seg.endswith("}"):
            continue
        if seg.lower() in _SKIP_PATH_SEGS:
            continue
        phrase = _split_ident(seg)
        if phrase:
            chunks.append(phrase)
    if op.source_label:
        chunks.append(op.source_label)
    chunks.extend(op.tags)
    return ". ".join(c for c in chunks if c) + "."


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def openapi_embeddings_path(shard_dir: str | Path) -> Path:
    """File-mode offline sidecar under Pgvector/ (product uses live vector store)."""
    return (
        Path(shard_dir)
        / "Pgvector"
        / "api_index"
        / "local"
        / "openapi_embeddings.json"
    )


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=True):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / math.sqrt(na * nb)


def load_openapi_index(path: str | Path) -> dict[str, OpenApiEmbeddingEntry]:
    p = Path(path)
    if not p.is_file():
        return {}
    raw: Any = json.loads(p.read_text(encoding="utf-8"))
    items = raw.get("operations") if isinstance(raw, dict) else None
    if not isinstance(items, list):
        return {}
    out: dict[str, OpenApiEmbeddingEntry] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        oid = item.get("id")
        vec = item.get("vector")
        text = item.get("text")
        th = item.get("text_hash")
        if not isinstance(oid, str) or not isinstance(vec, list):
            continue
        floats = [float(v) for v in vec if isinstance(v, (int, float))]
        if len(floats) != len(vec):
            continue
        out[oid] = OpenApiEmbeddingEntry(
            id=oid,
            text=str(text or ""),
            text_hash=str(th or ""),
            vector=floats,
        )
    return out


def save_openapi_index(path: str | Path, entries: dict[str, OpenApiEmbeddingEntry]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "operations": [
            {
                "id": e.id,
                "text": e.text,
                "text_hash": e.text_hash,
                "vector": e.vector,
            }
            for e in sorted(entries.values(), key=lambda x: x.id)
        ],
    }
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


def seed_cache_from_index(
    ops: list[ApiOperation],
    index: dict[str, OpenApiEmbeddingEntry],
    cache: dict[str, list[float]],
    *,
    hashes: dict[str, str] | None = None,
) -> None:
    """Copy valid sidecar vectors into the in-process cache; drop stale hashes."""
    for op in ops:
        text = operation_text(op)
        th = text_hash(text)
        if hashes is not None:
            hashes[op.id] = th
        entry = index.get(op.id)
        if entry is None:
            continue
        if entry.text_hash and entry.text_hash != th:
            continue
        cache[op.id] = list(entry.vector)


async def _embed_missing(
    ops: list[ApiOperation],
    *,
    embed: EmbedFn,
    cache: dict[str, list[float]],
    hashes: dict[str, str],
) -> None:
    sem = asyncio.Semaphore(_EMBED_CONCURRENCY)

    async def _one(op: ApiOperation) -> None:
        if op.id in cache:
            return
        text = operation_text(op)
        th = text_hash(text)
        hashes[op.id] = th
        async with sem:
            vec = await embed(text)
        cache[op.id] = list(vec)

    await asyncio.gather(*(_one(op) for op in ops))


async def search_operations_semantic(
    ops: list[ApiOperation],
    query: str,
    *,
    embed: EmbedFn,
    cache: dict[str, list[float]],
    limit: int = 15,
    hashes: dict[str, str] | None = None,
) -> list[ApiOperation]:
    """Cosine rank vs cached op vectors; blend 0.7 cosine + 0.3 keyword."""
    if not query.strip() or not ops:
        return ops[:limit]
    hash_map = hashes if hashes is not None else {}
    await _embed_missing(ops, embed=embed, cache=cache, hashes=hash_map)
    qvec = await embed(query.strip())
    keyword_hits = search_operations(ops, query, limit=max(limit * 3, 15))
    keyword_ids = {o.id for o in keyword_hits}
    scored: list[tuple[ApiOperation, float]] = []
    for op in ops:
        vec = cache.get(op.id)
        if vec is None:
            continue
        cos = _cosine(qvec, vec)
        hit = 1.0 if op.id in keyword_ids else 0.0
        score = 0.7 * cos + 0.3 * hit
        if score > 0.0:
            scored.append((op, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    if scored:
        return [o for o, _ in scored[:limit]]
    # No semantic scores — keyword hits only (never arbitrary first-N).
    return keyword_hits[:limit]


async def search_operations_with_embeddings(
    ops: list[ApiOperation],
    query: str,
    *,
    cache: dict[str, list[float]],
    limit: int = 15,
    embed: EmbedFn | None = None,
    hashes: dict[str, str] | None = None,
) -> tuple[list[ApiOperation], bool]:
    """Return (hits, used_semantic). Keyword fallback when embed fails."""
    if embed is None:
        return search_operations(ops, query, limit=limit), False
    try:
        hits = await search_operations_semantic(
            ops,
            query,
            embed=embed,
            cache=cache,
            limit=limit,
            hashes=hashes,
        )
        return hits, True
    except Exception:  # noqa: BLE001 — live embedder down → keyword
        return search_operations(ops, query, limit=limit), False
