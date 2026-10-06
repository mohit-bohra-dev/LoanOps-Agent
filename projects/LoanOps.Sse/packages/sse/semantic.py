"""Embed OpenAPI operations for search_sse_apis (in-process cache, not Qdrant)."""

from __future__ import annotations

import math
import re
from collections.abc import Awaitable, Callable
from packages.sse.catalog import search_operations
from packages.sse.types import ApiOperation

EmbedFn = Callable[[str], Awaitable[list[float]]]

_SKIP_PATH_SEGS = frozenset({"api", "v1", "v2", "v3", "v4", "internal", "external"})


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


async def search_operations_semantic(
    ops: list[ApiOperation],
    query: str,
    *,
    embed: EmbedFn,
    cache: dict[str, list[float]],
    limit: int = 15,
) -> list[ApiOperation]:
    """Cosine rank vs cached op vectors; blend 0.7 cosine + 0.3 keyword (Phase 9)."""
    if not query.strip() or not ops:
        return ops[:limit]
    qvec = await embed(query.strip())
    keyword_ids = {o.id for o in search_operations(ops, query, limit=max(limit * 3, 15))}
    by_id = {o.id: o for o in ops}
    scored: list[tuple[ApiOperation, float]] = []
    for op in ops:
        vec = cache.get(op.id)
        if vec is None:
            vec = await embed(operation_text(op))
            cache[op.id] = vec
        cos = _cosine(qvec, vec)
        hit = 1.0 if op.id in keyword_ids else 0.0
        score = 0.7 * cos + 0.3 * hit
        if score > 0.0:
            scored.append((op, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    if scored:
        return [o for o, _ in scored[:limit]]
    return list(by_id.values())[:limit]


async def search_operations_with_embeddings(
    ops: list[ApiOperation],
    query: str,
    *,
    cache: dict[str, list[float]],
    limit: int = 15,
    embed: EmbedFn | None = None,
) -> list[ApiOperation]:
    """Semantic when embed works; keyword otherwise."""
    if embed is None:
        return search_operations(ops, query, limit=limit)
    try:
        return await search_operations_semantic(
            ops, query, embed=embed, cache=cache, limit=limit
        )
    except Exception:  # noqa: BLE001 — live embedder down → keyword
        return search_operations(ops, query, limit=limit)
