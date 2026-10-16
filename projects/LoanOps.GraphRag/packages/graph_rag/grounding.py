"""Deterministic grounding filter for extracted entities/relations."""

from __future__ import annotations

import re
from typing import Any


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def ground_extraction(
    chunk_text: str,
    entities: list[dict[str, Any]],
    relations: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep entities whose names appear in chunk; relations whose endpoints co-occur.

    Returns (kept_entities, kept_relations, dropped_gap_items).
    """
    hay = normalize_ws(chunk_text)
    kept_entities: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    names: set[str] = set()

    for ent in entities:
        name = str(ent.get("name") or "").strip()
        if not name:
            dropped.append({"kind": "entity_empty", "entity": ent})
            continue
        if normalize_ws(name) not in hay:
            dropped.append({"kind": "entity_ungrounded", "entity": ent})
            continue
        kept_entities.append({"name": name, "type": str(ent.get("type") or "concept")})
        names.add(normalize_ws(name))

    kept_relations: list[dict[str, Any]] = []
    for rel in relations:
        src = str(rel.get("source") or "").strip()
        tgt = str(rel.get("target") or "").strip()
        if not src or not tgt:
            dropped.append({"kind": "relation_empty", "relation": rel})
            continue
        ns, nt = normalize_ws(src), normalize_ws(tgt)
        if ns not in hay or nt not in hay:
            dropped.append({"kind": "relation_ungrounded", "relation": rel})
            continue
        # Prefer endpoints that survived as entities; still allow if both in text.
        kept_relations.append(
            {
                "source": src,
                "target": tgt,
                "type": str(rel.get("type") or "related"),
            }
        )

    # Stable order
    kept_entities.sort(key=lambda e: (e["name"].lower(), e["type"]))
    kept_relations.sort(
        key=lambda r: (r["source"].lower(), r["target"].lower(), r["type"])
    )
    return kept_entities, kept_relations, dropped
