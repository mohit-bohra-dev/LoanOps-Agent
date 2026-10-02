"""Provenance-aware graph queries for MCP / pilot questions."""

from __future__ import annotations

from typing import Any

from packages.capability_kg.ontology import (
    CLASS_API_OPERATION,
    CLASS_CAPABILITY,
    CLASS_CROSS_APP_RELATIONSHIP,
    DEFAULT_NAMESPACE,
    PRED_BELONGS_TO_APP,
    PRED_FROM_APP,
    PRED_HAS_EVIDENCE,
    PRED_HTTP_METHOD,
    PRED_HTTP_PATH,
    PRED_IMPLEMENTED_BY,
    PRED_IMPLEMENTED_BY_CODE_UNIT,
    PRED_OPERATION_ID,
    PRED_RELATIONSHIP_KIND,
    PRED_REQUIRES_PERMISSION,
    PRED_REVIEW_STATUS,
    PRED_TO_APP,
    PRED_TO_OPERATION,
    PRED_TO_PACKAGE,
    loanops_ns,
)
from rdflib import Graph
from rdflib.namespace import RDF, RDFS


def _label(g: Graph, node: Any) -> str:
    for _, _, o in g.triples((node, RDFS.label, None)):
        return str(o)
    return str(node).rsplit("/", 1)[-1]


def _normalize_needle(value: str) -> str:
    return value.lower().replace(" ", "_").replace("-", "_")


def _score_match(needle: str, tokens: list[str], *parts: str) -> int | None:
    """Lower score = better. None = no match.

    0 exact (any part), 1 full-needle substring, 10-N multi-token hits.
    Short single tokens (len<=3) never match via tokens alone.
    """
    parts_n = [_normalize_needle(p) for p in parts if p]
    blob = " ".join(parts_n)
    if not blob or not needle:
        return None
    if any(p == needle for p in parts_n):
        return 0
    if needle in blob:
        return 1
    if not tokens:
        return None
    hits = sum(1 for t in tokens if t in blob)
    if hits == 0:
        return None
    if len(tokens) == 1 and len(tokens[0]) <= 3:
        return None
    if len(tokens) >= 2 and hits < max(2, (len(tokens) + 1) // 2):
        return None
    return 10 - hits


def _query_tokens(query: str) -> tuple[str, list[str]]:
    """Normalize query and derive tokens from snake + camelCase."""
    import re

    raw = query.strip()
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", raw)
    q = _normalize_needle(spaced)
    tokens = [t for t in q.replace("/", " ").split("_") if len(t) > 2]
    return q, tokens


def _operation_fields(
    g: Graph,
    op: Any,
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> dict[str, Any]:
    ns = loanops_ns(namespace)
    result: dict[str, Any] = {"operation_id": None}
    for _, _, oid in g.triples((op, ns[PRED_OPERATION_ID], None)):
        result["operation_id"] = str(oid)
    for _, _, m in g.triples((op, ns[PRED_HTTP_METHOD], None)):
        result["http_method"] = str(m)
    for _, _, p in g.triples((op, ns[PRED_HTTP_PATH], None)):
        result["http_path"] = str(p)
    for _, _, app in g.triples((op, ns[PRED_BELONGS_TO_APP], None)):
        result["application"] = _label(g, app)
    for _, _, code in g.triples((op, ns[PRED_IMPLEMENTED_BY_CODE_UNIT], None)):
        result["code_unit"] = _label(g, code)
    for _, _, perm in g.triples((op, ns[PRED_REQUIRES_PERMISSION], None)):
        result["permission"] = str(perm)
    for _, _, authz in g.triples((op, ns["authzSource"], None)):
        result["authz_source"] = str(authz)
    evidence: list[dict[str, str]] = []
    for _, _, ev in g.triples((op, ns[PRED_HAS_EVIDENCE], None)):
        row: dict[str, str] = {}
        for _, p, o in g.triples((ev, None, None)):
            row[str(p).rsplit("/", 1)[-1]] = str(o)
        evidence.append(row)
    result["evidence"] = evidence
    return result


def _explain_from_operation(
    g: Graph,
    op: Any,
    *,
    namespace: str,
    capability_id: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {"id": capability_id, "uri": str(op)}
    result.update(_operation_fields(g, op, namespace=namespace))
    return result


def explain_capability(
    g: Graph,
    capability_id: str,
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> dict[str, Any] | None:
    ns = loanops_ns(namespace)
    needle, _tokens = _query_tokens(capability_id)
    compact = _normalize_needle(capability_id)

    op_hits: list[tuple[int, Any, str]] = []
    for op, _, _ in g.triples((None, RDF.type, ns[CLASS_API_OPERATION])):
        oid = str(next(g.objects(op, ns[PRED_OPERATION_ID]), "") or "")
        on = _normalize_needle(oid)
        on_camel, _ = _query_tokens(oid)
        if not oid:
            continue
        if on == needle or on == compact or on_camel == needle:
            op_hits.append((0, op, oid))
        elif needle in on_camel or compact in on or needle in on:
            op_hits.append((1, op, oid))
        elif len(on_camel) >= 6 and (on_camel in needle or on in compact):
            op_hits.append((2, op, oid))
    if op_hits:
        op_hits.sort(key=lambda t: (t[0], len(t[2])))
        _, op, oid = op_hits[0]
        return _explain_from_operation(g, op, namespace=namespace, capability_id=oid)

    cap = None
    for s, _, _ in g.triples((None, RDF.type, ns[CLASS_CAPABILITY])):
        lab = _normalize_needle(_label(g, s))
        uri_tail = _normalize_needle(str(s).rsplit("/", 1)[-1])
        if needle in {lab, uri_tail} or compact in {lab, uri_tail}:
            cap = s
            break
        if needle in lab or needle in uri_tail or compact in lab or compact in uri_tail:
            cap = s
            break
    if cap is None:
        return None
    result: dict[str, Any] = {"id": _label(g, cap), "uri": str(cap)}
    for _, _, op in g.triples((cap, ns[PRED_IMPLEMENTED_BY], None)):
        result.update(_operation_fields(g, op, namespace=namespace))
    return result


def search_capabilities(
    g: Graph,
    query: str,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    limit: int = 20,
) -> list[dict[str, Any]]:
    ns = loanops_ns(namespace)
    q, tokens = _query_tokens(query)
    scored: list[tuple[int, dict[str, Any]]] = []
    seen: set[str] = set()

    def _add(score: int, row: dict[str, Any]) -> None:
        key = str(row.get("uri") or row.get("id") or "")
        if not key or key in seen:
            return
        seen.add(key)
        scored.append((score, row))

    for s, _, _ in g.triples((None, RDF.type, ns[CLASS_CAPABILITY])):
        label = _label(g, s)
        paths: list[str] = []
        oids: list[str] = []
        for _, _, op in g.triples((s, ns[PRED_IMPLEMENTED_BY], None)):
            for _, _, path in g.triples((op, ns[PRED_HTTP_PATH], None)):
                paths.append(str(path))
            for _, _, oid in g.triples((op, ns[PRED_OPERATION_ID], None)):
                oids.append(str(oid))
        score = _score_match(q, tokens, label, str(s), *paths, *oids)
        if score is None:
            continue
        _add(score, explain_capability(g, label, namespace=namespace) or {"id": label})

    for op, _, _ in g.triples((None, RDF.type, ns[CLASS_API_OPERATION])):
        oid = str(next(g.objects(op, ns[PRED_OPERATION_ID]), "") or "")
        path = str(next(g.objects(op, ns[PRED_HTTP_PATH]), "") or "")
        score = _score_match(q, tokens, oid, path)
        if score is None:
            continue
        _add(score, _explain_from_operation(g, op, namespace=namespace, capability_id=oid or path))

    scored.sort(key=lambda t: (t[0], str(t[1].get("id") or "")))
    return [row for _, row in scored[:limit]]


def find_providers(
    g: Graph,
    capability_or_op: str,
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> list[dict[str, Any]]:
    explained = explain_capability(g, capability_or_op, namespace=namespace)
    if explained and explained.get("application"):
        return [explained]
    return search_capabilities(g, capability_or_op, namespace=namespace, limit=10)


def impact_of_change(
    g: Graph,
    operation_or_app: str,
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> list[dict[str, Any]]:
    """Incoming callsOperation / consumesSdk edges with evidence."""
    ns = loanops_ns(namespace)
    needle = operation_or_app.lower()
    impacts: list[dict[str, Any]] = []
    for s, _, _ in g.triples((None, RDF.type, ns[CLASS_CROSS_APP_RELATIONSHIP])):
        kind = None
        for _, _, k in g.triples((s, ns[PRED_RELATIONSHIP_KIND], None)):
            kind = str(k)
        if kind not in {"callsOperation", "consumesSdk", "sharesDto", "callsApplication"}:
            continue
        status = str(next(g.objects(s, ns[PRED_REVIEW_STATUS]), "") or "")
        if status == "rejected":
            continue
        to_op = None
        to_pkg = None
        to_app = None
        from_app = None
        for _, _, o in g.triples((s, ns[PRED_TO_OPERATION], None)):
            to_op = str(o)
        for _, _, o in g.triples((s, ns[PRED_TO_PACKAGE], None)):
            to_pkg = str(o)
        for _, _, o in g.triples((s, ns[PRED_TO_APP], None)):
            to_app = _label(g, o)
        for _, _, o in g.triples((s, ns[PRED_FROM_APP], None)):
            from_app = _label(g, o)
        blob = " ".join(x for x in [kind, to_op, to_pkg, to_app] if x).lower()
        if needle not in blob and needle not in (to_app or "").lower():
            continue
        evidence = []
        for _, _, ev in g.triples((s, ns[PRED_HAS_EVIDENCE], None)):
            row: dict[str, str] = {}
            for _, p, o in g.triples((ev, None, None)):
                row[str(p).rsplit("/", 1)[-1]] = str(o)
            evidence.append(row)
        impacts.append(
            {
                "kind": kind,
                "review_status": status or "pending_review",
                "from_application": from_app,
                "to_application": to_app,
                "to_operation": to_op,
                "to_package": to_pkg,
                "evidence": evidence,
            }
        )
    impacts.sort(key=lambda r: 0 if r.get("review_status") == "approved" else 1)
    return impacts
