"""Offline capability embedding index (Phase 9). Not Qdrant. Not Graphify."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

EmbedFn = Callable[[str], Awaitable[list[float]]]

_DOMAIN_DEFAULT = "Loan Servicing"
_SKIP_PATH_SEGS = frozenset({"api", "v1", "v2", "v3", "v4", "internal", "external"})


class _CapLike(Protocol):
    id: str
    description: str | None
    operation_id: str | None
    http_path: str | None


@dataclass(frozen=True)
class EmbeddingEntry:
    id: str
    text: str
    text_hash: str
    vector: list[float]


def _split_ident(name: str) -> str:
    """Camel/snake/kebab → spaced words for denser embed tokens."""
    s = name.replace("_", " ").replace("-", " ")
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1 \2", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)
    return " ".join(s.split())


def _path_phrases(path: str) -> str:
    """Humanize URL segments; drop params and boilerplate (api/v1)."""
    parts: list[str] = []
    for seg in path.strip("/").split("/"):
        if not seg or seg.startswith("{") or seg.endswith("}"):
            continue
        if seg.lower() in _SKIP_PATH_SEGS:
            continue
        phrase = _split_ident(seg)
        if phrase:
            parts.append(phrase)
    return " ".join(parts)


def capability_text(rec: _CapLike, *, domain: str = _DOMAIN_DEFAULT) -> str:
    """Rich embed string: id + summary + op + HTTP path phrases."""
    desc = (rec.description or "").strip()
    op = (rec.operation_id or "").strip()
    path = (getattr(rec, "http_path", None) or "").strip()
    readable = rec.id.replace("_", " ")
    chunks: list[str] = [readable]
    if desc:
        chunks.append(desc)
    if op:
        chunks.append(f"operation {op}")
        split_op = _split_ident(op)
        if split_op and split_op.lower() != readable.lower():
            chunks.append(split_op)
    if path:
        chunks.append(f"path {path}")
        phrases = _path_phrases(path)
        if phrases:
            chunks.append(phrases)
    chunks.append(f"domain {domain}")
    return ". ".join(chunks) + "."


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def embeddings_path_for_ttl(ttl_path: str | Path) -> Path:
    p = Path(ttl_path)
    return p.with_name("embeddings.json")


def embeddings_path_for_shards(shard_dir: str | Path) -> Path:
    """Sidecar for merged EAKG (gitignored under data/eakg/enterprise/)."""
    return Path(shard_dir) / "enterprise" / "embeddings.json"


def cosine(a: list[float], b: list[float]) -> float:
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


def load_index(path: str | Path) -> dict[str, EmbeddingEntry]:
    p = Path(path)
    if not p.is_file():
        return {}
    raw: Any = json.loads(p.read_text(encoding="utf-8"))
    items = raw.get("capabilities") if isinstance(raw, dict) else None
    if not isinstance(items, list):
        return {}
    out: dict[str, EmbeddingEntry] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        cid = item.get("id")
        vec = item.get("vector")
        text = item.get("text")
        th = item.get("text_hash")
        if not isinstance(cid, str) or not isinstance(vec, list):
            continue
        floats = [float(v) for v in vec if isinstance(v, (int, float))]
        if len(floats) != len(vec):
            continue
        out[cid] = EmbeddingEntry(
            id=cid,
            text=str(text or ""),
            text_hash=str(th or ""),
            vector=floats,
        )
    return out


def save_index(path: str | Path, entries: dict[str, EmbeddingEntry]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "capabilities": [
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


async def build_index(
    records: Sequence[Any],
    embed: EmbedFn,
    *,
    domain: str = _DOMAIN_DEFAULT,
) -> dict[str, EmbeddingEntry]:
    """Embed each capability text. Caller owns the EmbeddingProvider."""
    out: dict[str, EmbeddingEntry] = {}
    for rec in records:
        cid = getattr(rec, "id", None)
        if not isinstance(cid, str) or not cid:
            continue
        text = capability_text(rec, domain=domain)
        vector = await embed(text)
        out[cid] = EmbeddingEntry(
            id=cid,
            text=text,
            text_hash=text_hash(text),
            vector=list(vector),
        )
    return out


def rank(
    query_vector: list[float],
    index: dict[str, EmbeddingEntry],
    *,
    top_k: int = 15,
) -> list[tuple[str, float]]:
    scored: list[tuple[str, float]] = []
    for cid, entry in index.items():
        scored.append((cid, cosine(query_vector, entry.vector)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]
