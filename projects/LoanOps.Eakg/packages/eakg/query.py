"""Provenance-aware graph queries for MCP / pilot questions (SPARQL, ADR-026)."""

from __future__ import annotations

from typing import Any

from packages.capability_kg.ontology import DEFAULT_NAMESPACE
from packages.common.providers.graph_store import AbstractGraphStore, GraphStoreError


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


def _binding_str(row: dict[str, Any], key: str) -> str | None:
    cell = row.get(key)
    if not isinstance(cell, dict):
        return None
    val = cell.get("value")
    return str(val) if val is not None else None


def _app_label(row: dict[str, Any], label_key: str, uri_key: str) -> str | None:
    """Prefer rdfs:label; else URI local name with optional ``app_`` prefix stripped."""
    lab = _binding_str(row, label_key)
    if lab:
        return lab.rsplit("/", 1)[-1] if "/" in lab else lab
    uri = _binding_str(row, uri_key)
    if not uri:
        return None
    local = uri.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
    if local.startswith("app_"):
        return local[4:] or local
    return local or None


def _prefix_block(namespace: str) -> str:
    base = namespace if namespace.endswith("/") or namespace.endswith("#") else f"{namespace}/"
    return f"PREFIX lo: <{base}>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"


def _row_from_op_binding(row: dict[str, Any], *, capability_id: str | None = None) -> dict[str, Any]:
    oid = _binding_str(row, "oid") or capability_id or ""
    method = _binding_str(row, "method")
    path = _binding_str(row, "path")
    app = _app_label(row, "appLabel", "app")
    code = _binding_str(row, "codeLabel") or _binding_str(row, "code")
    if code and "/" in code:
        code = code.rsplit("/", 1)[-1]
        if code.startswith("code_"):
            code = code[5:] or code
    result: dict[str, Any] = {
        "id": oid,
        "uri": _binding_str(row, "op") or "",
        "operation_id": oid or None,
        "http_method": method,
        "http_path": path,
        "application": app,
        "code_unit": code,
        "permission": _binding_str(row, "perm"),
        "authz_source": _binding_str(row, "authz"),
        "evidence": [],
        "mcp_invoke": (method or "").upper() == "GET",
    }
    return result


_OPS_SELECT = """
SELECT ?op ?oid ?method ?path ?app ?appLabel ?code ?codeLabel ?perm ?authz
WHERE {
  GRAPH ?g {
    ?op a lo:APIOperation ;
        lo:operationId ?oid .
    OPTIONAL { ?op lo:httpMethod ?method }
    OPTIONAL { ?op lo:httpPath ?path }
    OPTIONAL {
      ?op lo:belongsToApp ?app .
      OPTIONAL { ?app rdfs:label ?appLabel }
    }
    OPTIONAL {
      ?op lo:implementedByCodeUnit ?code .
      OPTIONAL { ?code rdfs:label ?codeLabel }
    }
    OPTIONAL { ?op lo:requiresPermission ?perm }
    OPTIONAL { ?op lo:authzSource ?authz }
  }
}
"""


async def _fetch_operations(
    store: AbstractGraphStore,
    *,
    namespace: str,
) -> list[dict[str, Any]]:
    data = await store.query(_prefix_block(namespace) + _OPS_SELECT)
    return list(data.get("results", {}).get("bindings", []))


async def list_operation_records(
    store: AbstractGraphStore,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    limit: int = 10_000,
) -> list[dict[str, Any]]:
    """All APIOperation rows (for capability bind warm / diagnostics)."""
    rows = await _fetch_operations(store, namespace=namespace)
    out = [_row_from_op_binding(r, capability_id=_binding_str(r, "oid") or "") for r in rows]
    return out[:limit]


async def _fetch_evidence_for_subject(
    store: AbstractGraphStore,
    subject_uri: str,
    *,
    namespace: str,
) -> list[dict[str, str]]:
    sparql = (
        _prefix_block(namespace)
        + f"""
SELECT ?ev ?pred ?obj WHERE {{
  GRAPH ?g {{
    <{subject_uri}> lo:hasEvidence ?ev .
    ?ev ?pred ?obj .
  }}
}}
"""
    )
    data = await store.query(sparql)
    by_ev: dict[str, dict[str, str]] = {}
    for row in data.get("results", {}).get("bindings", []):
        ev = _binding_str(row, "ev") or "_"
        pred = _binding_str(row, "pred") or ""
        obj = _binding_str(row, "obj") or ""
        key = pred.rsplit("/", 1)[-1] if pred else "value"
        by_ev.setdefault(ev, {})[key] = obj
    return list(by_ev.values())


async def explain_capability(
    store: AbstractGraphStore,
    capability_id: str,
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> dict[str, Any] | None:
    needle, _tokens = _query_tokens(capability_id)
    compact = _normalize_needle(capability_id)
    ops = await _fetch_operations(store, namespace=namespace)

    op_hits: list[tuple[int, dict[str, Any], str]] = []
    for row in ops:
        oid = _binding_str(row, "oid") or ""
        if not oid:
            continue
        on = _normalize_needle(oid)
        on_camel, _ = _query_tokens(oid)
        if on == needle or on == compact or on_camel == needle:
            op_hits.append((0, row, oid))
        elif needle in on_camel or compact in on or needle in on:
            op_hits.append((1, row, oid))
        elif len(on_camel) >= 6 and (on_camel in needle or on in compact):
            op_hits.append((2, row, oid))
    if op_hits:
        op_hits.sort(key=lambda t: (t[0], len(t[2])))
        _, row, oid = op_hits[0]
        result = _row_from_op_binding(row, capability_id=oid)
        op_uri = _binding_str(row, "op")
        if op_uri:
            result["evidence"] = await _fetch_evidence_for_subject(
                store, op_uri, namespace=namespace
            )
        return result

    # Capability nodes (label / URI tail)
    sparql = (
        _prefix_block(namespace)
        + """
SELECT ?cap ?label ?op ?oid ?method ?path ?app ?appLabel ?code ?codeLabel ?perm ?authz
WHERE {
  GRAPH ?g {
    ?cap a lo:Capability .
    OPTIONAL { ?cap rdfs:label ?label }
    OPTIONAL {
      ?cap lo:implementedBy ?op .
      OPTIONAL { ?op lo:operationId ?oid }
      OPTIONAL { ?op lo:httpMethod ?method }
      OPTIONAL { ?op lo:httpPath ?path }
      OPTIONAL {
        ?op lo:belongsToApp ?app .
        OPTIONAL { ?app rdfs:label ?appLabel }
      }
      OPTIONAL {
        ?op lo:implementedByCodeUnit ?code .
        OPTIONAL { ?code rdfs:label ?codeLabel }
      }
      OPTIONAL { ?op lo:requiresPermission ?perm }
      OPTIONAL { ?op lo:authzSource ?authz }
    }
  }
}
"""
    )
    data = await store.query(sparql)
    for row in data.get("results", {}).get("bindings", []):
        lab = _normalize_needle(_binding_str(row, "label") or "")
        uri = _binding_str(row, "cap") or ""
        uri_tail = _normalize_needle(uri.rsplit("/", 1)[-1])
        if needle in {lab, uri_tail} or compact in {lab, uri_tail}:
            pass
        elif needle in lab or needle in uri_tail or compact in lab or compact in uri_tail:
            pass
        else:
            continue
        label = _binding_str(row, "label") or uri_tail
        result = _row_from_op_binding(row, capability_id=label)
        result["id"] = label
        result["uri"] = uri
        return result
    return None


async def _search_capability_rows(
    store: AbstractGraphStore,
    query: str,
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> list[dict[str, Any]]:
    """Score-ranked capability/operation rows (all HTTP methods)."""
    q, tokens = _query_tokens(query)
    scored: list[tuple[int, dict[str, Any]]] = []
    seen: set[str] = set()

    def _add(score: int, row: dict[str, Any]) -> None:
        key = str(row.get("uri") or row.get("id") or "")
        if not key or key in seen:
            return
        seen.add(key)
        scored.append((score, row))

    ops = await _fetch_operations(store, namespace=namespace)
    for row in ops:
        oid = _binding_str(row, "oid") or ""
        path = _binding_str(row, "path") or ""
        score = _score_match(q, tokens, oid, path)
        if score is None:
            continue
        _add(score, _row_from_op_binding(row, capability_id=oid or path))

    sparql = (
        _prefix_block(namespace)
        + """
SELECT ?cap ?label ?oid ?path WHERE {
  GRAPH ?g {
    ?cap a lo:Capability .
    OPTIONAL { ?cap rdfs:label ?label }
    OPTIONAL {
      ?cap lo:implementedBy ?op .
      OPTIONAL { ?op lo:operationId ?oid }
      OPTIONAL { ?op lo:httpPath ?path }
    }
  }
}
"""
    )
    data = await store.query(sparql)
    for row in data.get("results", {}).get("bindings", []):
        label = _binding_str(row, "label") or ""
        uri = _binding_str(row, "cap") or ""
        oid = _binding_str(row, "oid") or ""
        path = _binding_str(row, "path") or ""
        score = _score_match(q, tokens, label, uri, path, oid)
        if score is None:
            continue
        explained = await explain_capability(store, label or uri, namespace=namespace)
        _add(score, explained or {"id": label or uri, "uri": uri})

    scored.sort(key=lambda t: (t[0], str(t[1].get("id") or "")))
    return [row for _, row in scored]


async def search_capabilities(
    store: AbstractGraphStore,
    query: str,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Invoke-oriented search: prefer GET when any GET hit exists."""
    rows = await _search_capability_rows(store, query, namespace=namespace)
    reads = [row for row in rows if str(row.get("http_method") or "").upper() == "GET"]
    chosen = reads if reads else rows
    out = chosen[:limit]
    omitted = len(rows) - len(reads) if reads else 0
    if omitted > 0 and out:
        out[0] = {**out[0], "non_get_omitted": omitted}
    return out


async def find_providers(
    store: AbstractGraphStore,
    capability_or_op: str,
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> list[dict[str, Any]]:
    """Discovery/impact: all methods. mcp_invoke marks call_sse_api eligibility."""
    explained = await explain_capability(store, capability_or_op, namespace=namespace)
    if explained and explained.get("application"):
        return [explained]
    return (await _search_capability_rows(store, capability_or_op, namespace=namespace))[:10]


async def impact_of_change(
    store: AbstractGraphStore,
    operation_or_app: str,
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> list[dict[str, Any]]:
    """Incoming callsOperation / consumesSdk edges with evidence."""
    needle = operation_or_app.lower()
    sparql = (
        _prefix_block(namespace)
        + """
SELECT ?rel ?kind ?status ?toOp ?toPkg ?toApp ?toAppLabel ?fromApp ?fromAppLabel
WHERE {
  GRAPH ?g {
    ?rel a lo:CrossAppRelationship ;
         lo:relationshipKind ?kind .
    OPTIONAL { ?rel lo:hasReviewStatus ?status }
    OPTIONAL { ?rel lo:toOperation ?toOp }
    OPTIONAL { ?rel lo:toPackage ?toPkg }
    OPTIONAL {
      ?rel lo:toApplication ?toApp .
      OPTIONAL { ?toApp rdfs:label ?toAppLabel }
    }
    OPTIONAL {
      ?rel lo:fromApplication ?fromApp .
      OPTIONAL { ?fromApp rdfs:label ?fromAppLabel }
    }
  }
}
"""
    )
    try:
        data = await store.query(sparql)
    except GraphStoreError:
        raise
    impacts: list[dict[str, Any]] = []
    for row in data.get("results", {}).get("bindings", []):
        kind = _binding_str(row, "kind")
        if kind not in {"callsOperation", "consumesSdk", "sharesDto", "callsApplication"}:
            continue
        status = _binding_str(row, "status") or ""
        if status == "rejected":
            continue
        to_op = _binding_str(row, "toOp")
        to_pkg = _binding_str(row, "toPkg")
        to_app = _app_label(row, "toAppLabel", "toApp")
        from_app = _app_label(row, "fromAppLabel", "fromApp")
        blob = " ".join(x for x in [kind, to_op, to_pkg, to_app] if x).lower()
        if needle not in blob and needle not in (to_app or "").lower():
            continue
        rel_uri = _binding_str(row, "rel") or ""
        evidence: list[dict[str, str]] = []
        if rel_uri:
            evidence = await _fetch_evidence_for_subject(store, rel_uri, namespace=namespace)
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
