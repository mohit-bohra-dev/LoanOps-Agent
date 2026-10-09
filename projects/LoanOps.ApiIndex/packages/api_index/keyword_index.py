"""Inverted keyword index over unified operations (spec §3.5)."""

from __future__ import annotations

import re
from collections import defaultdict

from packages.api_index.records import UnifiedOperation, alias_key
from packages.sse.types import ApiOperation

_TOKEN_SPLIT = re.compile(r"[\s,/|._\-]+")


def _split_ident(name: str) -> str:
    s = name.replace("_", " ").replace("-", " ")
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1 \2", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)
    return " ".join(s.split())


def _tokens(text: str) -> list[str]:
    """Tokenize like catalog.search_operations, with camelCase split."""
    expanded = _split_ident(text)
    return [t for t in _TOKEN_SPLIT.split(expanded.lower()) if t]


def _op_haystack(op: UnifiedOperation) -> str:
    op_part = op.public_id.split(":", 1)[-1] if ":" in op.public_id else op.public_id
    parts = [
        op.public_id,
        op_part,
        op.eakg_operation_key or "",
        op.summary or "",
        op.description or "",
        op.path,
        op.method,
        op.application_label,
        op.code_unit or "",
        *op.tags,
        *op.capability_ids,
        *[p.name for p in op.parameters],
    ]
    return " ".join(p for p in parts if p)


class KeywordIndex:
    """Token → uid postings; graded score = matched_query_tokens / query_tokens."""

    def __init__(self, operations: list[UnifiedOperation] | None = None) -> None:
        self._ops = list(operations or [])
        self._by_uid = {op.uid: op for op in self._ops}
        self._postings: dict[str, set[str]] = defaultdict(set)
        # exact name key → apps (operationId / eakg_key alias_key)
        self._exact_name_apps: dict[str, set[str]] = defaultdict(set)
        for op in self._ops:
            for tok in _tokens(_op_haystack(op)):
                self._postings[tok].add(op.uid)
            op_part = op.public_id.split(":", 1)[-1] if ":" in op.public_id else ""
            for raw in (op_part, op.eakg_operation_key or ""):
                key = alias_key(raw)
                if key:
                    self._exact_name_apps[key].add(op.application_id)

    def suggest(self, query: str, *, limit: int = 3) -> list[str]:
        scored = self.score(query, limit=limit)
        return [
            self._by_uid[uid].public_id
            for uid, _ in sorted(scored.items(), key=lambda kv: (-kv[1], self._by_uid[kv[0]].public_id))
            if uid in self._by_uid
        ][:limit]

    def score(
        self,
        query: str,
        *,
        apps: list[str] | None = None,
        limit: int | None = None,
    ) -> dict[str, float]:
        """Return uid → keyword score in [0, 1]."""
        q_tokens = _tokens(query)
        if not q_tokens:
            return {}
        app_set = set(apps) if apps is not None else None
        matched: dict[str, set[str]] = defaultdict(set)
        for tok in q_tokens:
            for uid in self._postings.get(tok, ()):
                op = self._by_uid.get(uid)
                if op is None:
                    continue
                if app_set is not None and op.application_id not in app_set:
                    continue
                matched[uid].add(tok)
        denom = float(len(q_tokens))
        scored = {uid: len(toks) / denom for uid, toks in matched.items()}
        if limit is None or limit <= 0:
            return scored
        ordered = sorted(
            scored.items(),
            key=lambda kv: (-kv[1], self._by_uid[kv[0]].public_id if kv[0] in self._by_uid else kv[0]),
        )
        return dict(ordered[:limit])

    def exact_name_apps(self, query: str) -> list[str]:
        """Apps owning an op whose operationId/eakg_key matches a query token exactly."""
        apps: set[str] = set()
        for tok in _tokens(query):
            key = alias_key(tok)
            if key:
                apps.update(self._exact_name_apps.get(key, ()))
            # also try the raw token as a whole-query name
        whole = alias_key(query.strip())
        if whole:
            apps.update(self._exact_name_apps.get(whole, ()))
        return sorted(apps)

    def to_api_operations(self, uids: list[str]) -> list[ApiOperation]:
        out: list[ApiOperation] = []
        for uid in uids:
            op = self._by_uid.get(uid)
            if op is not None:
                out.append(unified_to_api_operation(op))
        return out


def unified_to_api_operation(op: UnifiedOperation) -> ApiOperation:
    op_part = op.public_id.split(":", 1)[-1] if ":" in op.public_id else None
    return ApiOperation(
        id=op.public_id,
        source_id=op.application_id,
        source_label=op.application_label,
        method=op.method,
        path=op.path,
        operation_id=op_part,
        summary=op.summary,
        description=op.description,
        tags=list(op.tags),
        parameters=list(op.parameters),
        has_request_body=op.has_request_body,
        server_url=op.server_url,
        source_base_url=op.source_base_url,
    )
