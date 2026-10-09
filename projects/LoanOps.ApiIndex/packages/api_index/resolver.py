"""Alias resolution over unified operations (spec §3.3)."""

from __future__ import annotations

from packages.api_index.keyword_index import KeywordIndex
from packages.api_index.records import (
    Ambiguous,
    NotFound,
    Resolved,
    UnifiedOperation,
    alias_key,
)


def _aliases(rec: UnifiedOperation) -> set[str]:
    out: set[str] = {rec.public_id.lower(), rec.uid.lower()}
    app = rec.application_id
    op_part = rec.public_id.split(":", 1)[-1] if ":" in rec.public_id else ""
    if op_part:
        out.add(f"{app}:{alias_key(op_part)}")
        out.add(alias_key(op_part))
    if rec.eakg_operation_key:
        out.add(f"{app}:{alias_key(rec.eakg_operation_key)}")
        out.add(alias_key(rec.eakg_operation_key))
    for cid in rec.capability_ids:
        out.add(alias_key(cid))
    return out


class OperationResolver:
    """O(1) alias lookup. Never guesses when more than one hit."""

    def __init__(
        self,
        operations: list[UnifiedOperation],
        *,
        keyword_index: KeywordIndex | None = None,
    ) -> None:
        self._ops = list(operations)
        self._by_uid = {op.uid: op for op in self._ops}
        self._alias: dict[str, list[UnifiedOperation]] = {}
        for rec in self._ops:
            for key in _aliases(rec):
                bucket = self._alias.setdefault(key, [])
                if rec.uid not in {o.uid for o in bucket}:
                    bucket.append(rec)
        self._keyword = keyword_index or KeywordIndex(self._ops)

    def resolve(
        self,
        ref: str,
        *,
        application_id: str | None = None,
    ) -> Resolved | Ambiguous | NotFound:
        raw = (ref or "").strip()
        if not raw:
            return NotFound(ref=ref, suggestions=[])
        keys = {raw.lower(), alias_key(raw)}
        hits: list[UnifiedOperation] = []
        seen: set[str] = set()
        for key in keys:
            for rec in self._alias.get(key, []):
                if rec.uid in seen:
                    continue
                seen.add(rec.uid)
                hits.append(rec)
        if application_id:
            hits = [h for h in hits if h.application_id == application_id]
        if len(hits) == 1:
            return Resolved(record=hits[0], matched_alias=raw)
        if len(hits) > 1:
            cands = sorted(
                {(h.public_id, h.application_label) for h in hits},
                key=lambda t: t[0],
            )
            return Ambiguous(ref=raw, candidates=cands)
        return NotFound(ref=raw, suggestions=self._keyword.suggest(raw, limit=3))

    def get_by_public_id(self, public_id: str) -> UnifiedOperation | None:
        key = public_id.strip().lower()
        hits = self._alias.get(key, [])
        return hits[0] if len(hits) == 1 else self._by_uid.get(public_id)
