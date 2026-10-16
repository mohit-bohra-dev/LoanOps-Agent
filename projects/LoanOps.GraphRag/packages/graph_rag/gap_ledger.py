"""Gap-ledger *shape* for dropped extractions (copy; do not import packages.eakg)."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class LedgerItem:
    item_id: str
    shape_key: str
    source: str  # extract
    kind: str
    repository_id: str = "docs"
    context: dict[str, Any] = field(default_factory=dict)
    status: str = "open"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _id(*parts: str) -> str:
    blob = "|".join(parts).encode("utf-8")
    return "gap_" + hashlib.sha256(blob).hexdigest()[:16]


def shape_key(kind: str, feature: str) -> str:
    feat = feature.strip().lower().replace(" ", "_")[:80]
    return f"extract:{kind}:{feat}"


def from_dropped(
    chunk_id: str,
    path: str,
    dropped: list[dict[str, Any]],
) -> list[LedgerItem]:
    """Turn grounding/PII drops into ledger rows."""
    out: list[LedgerItem] = []
    for i, row in enumerate(dropped):
        kind = str(row.get("kind") or "unknown")
        feat = kind
        if "entity" in row and isinstance(row["entity"], dict):
            feat = str(row["entity"].get("name") or kind)
        elif "relation" in row and isinstance(row["relation"], dict):
            rel = row["relation"]
            feat = f"{rel.get('source')}-{rel.get('target')}"
        out.append(
            LedgerItem(
                item_id=_id(chunk_id, kind, feat, str(i)),
                shape_key=shape_key(kind, feat),
                source="extract",
                kind=kind,
                context={"chunk_id": chunk_id, "path": path, "detail": row},
            )
        )
    return out
