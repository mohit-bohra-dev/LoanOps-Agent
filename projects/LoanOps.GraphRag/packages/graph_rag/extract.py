"""Per-chunk LLM extraction with cache + grounding + PII scrub."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Protocol

from packages.graph_rag.cache import cache_key, read_cache, write_cache
from packages.graph_rag.gap_ledger import LedgerItem, from_dropped
from packages.graph_rag.grounding import ground_extraction
from packages.graph_rag.pii_scrub import scrub_extraction
from packages.graph_rag.schema import (
    EXTRACT_SYSTEM,
    EXTRACT_USER_TEMPLATE,
    PROMPT_VERSION,
    SCHEMA_VERSION,
)

logger = logging.getLogger(__name__)


class _ChatLike(Protocol):
    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> Any: ...


def _parse_payload(raw: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    data = json.loads(text)
    if not isinstance(data, dict):
        return [], []
    ents = data.get("entities") or []
    rels = data.get("relations") or []
    if not isinstance(ents, list):
        ents = []
    if not isinstance(rels, list):
        rels = []
    return [e for e in ents if isinstance(e, dict)], [r for r in rels if isinstance(r, dict)]


async def extract_chunk(
    *,
    chunk_id: str,
    path: str,
    content: str,
    model_id: str,
    chat: _ChatLike,
    cache_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[LedgerItem], bool]:
    """Return (entities, relations, gap_items, cache_hit)."""
    key = cache_key(
        content,
        model_id=model_id,
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
    )
    cached = read_cache(cache_dir, key)
    cache_hit = cached is not None
    if cached is not None:
        ents = list(cached.get("entities") or [])
        rels = list(cached.get("relations") or [])
        ents = [e for e in ents if isinstance(e, dict)]
        rels = [r for r in rels if isinstance(r, dict)]
    else:
        prompt = EXTRACT_USER_TEMPLATE.format(path=path, text=content[:12000])
        resp = await chat.complete(
            prompt,
            system=EXTRACT_SYSTEM,
            temperature=0.0,
            max_tokens=1024,
            json_mode=True,
        )
        raw = getattr(resp, "content", None) or str(resp)
        try:
            ents, rels = _parse_payload(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning("extract parse failed for %s; empty", chunk_id)
            ents, rels = [], []
        write_cache(
            cache_dir,
            key,
            {
                "entities": ents,
                "relations": rels,
                "model_id": model_id,
                "prompt_version": PROMPT_VERSION,
                "schema_version": SCHEMA_VERSION,
            },
        )

    ents, rels, drop_g = ground_extraction(content, ents, rels)
    ents, rels, drop_p = scrub_extraction(ents, rels)
    gaps = from_dropped(chunk_id, path, drop_g + drop_p)
    return ents, rels, gaps, cache_hit
