"""Inverted keyword index over unified operations (Phase 3)."""

from __future__ import annotations

from packages.api_index.records import UnifiedOperation


class KeywordIndex:
    """Placeholder until P3 two-stage search lands."""

    def __init__(self, operations: list[UnifiedOperation] | None = None) -> None:
        self._ops = list(operations or [])

    def suggest(self, query: str, *, limit: int = 3) -> list[str]:
        q = query.lower().strip()
        if not q:
            return []
        hits = [op.public_id for op in self._ops if q in op.public_id.lower()]
        return hits[:limit]
