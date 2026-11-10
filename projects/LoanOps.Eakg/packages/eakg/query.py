"""Provenance-aware graph queries for MCP / pilot questions (SPARQL, ADR-026)."""

from __future__ import annotations

import time
from typing import Any

from packages.capability_kg.ontology import DEFAULT_NAMESPACE
from packages.common.providers.graph_store import AbstractGraphStore, GraphStoreError

# Process-local TTL cache for full-graph SPARQL dumps used by capability search.
# Neither dump depends on the search query string.
_SPARQL_DUMP_TTL_S = 60.0
_ops_dump_cache: dict[tuple[int, str], tuple[float, list[dict[str, Any]]]] = {}
_caps_dump_cache: dict[tuple[int, str], tuple[float, list[dict[str, Any]]]] = {}


async def _traced_query(
    store: AbstractGraphStore,
    sparql: str,
    *,
    operation: str = "sparql",
) -> dict[str, Any]:
    """Run SPARQL under an ``eakg.sparql_query`` sub-span when telemetry is available."""
    from contextlib import asynccontextmanager
    from collections.abc import AsyncIterator

    @asynccontextmanager
    async def _span() -> AsyncIterator[Any]:
        try:
            from packages.common.providers.factory import get_telemetry_provider

            tel = get_telemetry_provider()
            async with tel.span(
                "eakg.sparql_query",
                attributes={"operation": operation, "span.kind": "subtool"},
                kind="subtool",
            ) as ctx:
                yield ctx
            return
        except Exception:  # noqa: BLE001
            pass
        from packages.common.providers.telemetry import trace_span

        async with trace_span(
            "eakg.sparql_query",
            attributes={"operation": operation},
            kind="subtool",
        ) as ctx:
            yield ctx

    async with _span() as span:
        try:
            data = await store.query(sparql)
            bindings = data.get("results", {}).get("bindings", []) if isinstance(data, dict) else []
            span.attributes["binding_count"] = len(bindings)
            span.output = {"binding_count": len(bindings)}
            return data if isinstance(data, dict) else {"results": {"bindings": []}}
        except Exception as exc:
            span.is_error = True
            span.error_message = str(exc)
            raise


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

_CAPS_SELECT = """
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


def _cache_get(
    cache: dict[tuple[int, str], tuple[float, list[dict[str, Any]]]],
    key: tuple[int, str],
) -> list[dict[str, Any]] | None:
    hit = cache.get(key)
    if hit is None:
        return None
    expires_at, rows = hit
    if time.monotonic() >= expires_at:
        cache.pop(key, None)
        return None
    return rows


def _cache_put(
    cache: dict[tuple[int, str], tuple[float, list[dict[str, Any]]]],
    key: tuple[int, str],
    rows: list[dict[str, Any]],
) -> None:
    cache[key] = (time.monotonic() + _SPARQL_DUMP_TTL_S, rows)


def clear_sparql_dump_caches() -> None:
    """Test helper: drop process-local SPARQL dump caches."""
    _ops_dump_cache.clear()
    _caps_dump_cache.clear()


async def _fetch_operations(
    store: AbstractGraphStore,
    *,
    namespace: str,
) -> list[dict[str, Any]]:
    key = (id(store), namespace)
    cached = _cache_get(_ops_dump_cache, key)
    if cached is not None:
        return cached
    data = await _traced_query(
        store, _prefix_block(namespace) + _OPS_SELECT, operation="fetch_operations"
    )
    rows = list(data.get("results", {}).get("bindings", []))
    _cache_put(_ops_dump_cache, key, rows)
    return rows


async def _fetch_capabilities(
    store: AbstractGraphStore,
    *,
    namespace: str,
) -> list[dict[str, Any]]:
    """Full Capability→op projection (same shape as explain_capability SELECT)."""
    key = (id(store), namespace)
    cached = _cache_get(_caps_dump_cache, key)
    if cached is not None:
        return cached
    data = await _traced_query(
        store,
        _prefix_block(namespace) + _CAPS_SELECT,
        operation="search_capabilities",
    )
    rows = list(data.get("results", {}).get("bindings", []))
    _cache_put(_caps_dump_cache, key, rows)
    return rows


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
    data = await _traced_query(store, sparql, operation="evidence")
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
    data = await _traced_query(store, sparql, operation="explain_capability")
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
    """Score-ranked capability/operation rows (all HTTP methods).

    Builds capability hits from a single full-projection SPARQL dump — no
    per-hit ``explain_capability`` (avoids N+1 SPARQL).
    """
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

    caps = await _fetch_capabilities(store, namespace=namespace)
    for row in caps:
        label = _binding_str(row, "label") or ""
        uri = _binding_str(row, "cap") or ""
        uri_tail = uri.rsplit("/", 1)[-1] if uri else ""
        oid = _binding_str(row, "oid") or ""
        path = _binding_str(row, "path") or ""
        score = _score_match(q, tokens, label, uri, path, oid)
        if score is None:
            continue
        cap_id = label or uri_tail or uri
        result = _row_from_op_binding(row, capability_id=cap_id)
        result["id"] = cap_id
        result["uri"] = uri
        _add(score, result)

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
        data = await _traced_query(store, sparql, operation="impact_of_change")
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


def _describe_from_interface(
    iface: Any,
    *,
    application_id: str,
) -> dict[str, Any]:
    """Structured describe payload from RepoInterface (JSON fallback)."""
    proxies: list[dict[str, Any]] = []
    for p in iface.proxies:
        if not isinstance(p, dict):
            continue
        proxies.append(
            {
                "class": p.get("class") or p.get("class_name"),
                "base": p.get("base") or p.get("base_class"),
                "url_key": p.get("url_key"),
            }
        )
    packages: list[dict[str, Any]] = []
    for p in iface.packages:
        if not isinstance(p, dict):
            continue
        packages.append(
            {
                "package_id": p.get("package_id") or p.get("id"),
                "version": p.get("version"),
            }
        )
    topics: list[dict[str, Any]] = []
    for t in iface.topics:
        if not isinstance(t, dict):
            continue
        topics.append(
            {
                "name": t.get("value") or t.get("key") or t.get("topic_name"),
                "role": t.get("role"),
            }
        )
    routes: list[dict[str, Any]] = []
    for r in iface.route_compositions:
        if not isinstance(r, dict):
            continue
        routes.append(
            {
                "path": r.get("path") or r.get("composed_path"),
                "caller": r.get("caller") or r.get("caller_symbol"),
                "method": r.get("method") or r.get("http_method"),
                "url_key": r.get("url_key"),
            }
        )
    return {
        "application_id": application_id or iface.application_id,
        "repository_id": iface.repository_id,
        "commit_sha": iface.commit_sha,
        "source": "interface",
        "proxies": proxies,
        "packages": packages,
        "topics": topics,
        "connection_keys": list(iface.connection_keys),
        "service_url_keys": list(iface.service_url_keys),
        "route_compositions": routes,
        "operation_count": len(iface.operations),
    }


def _sparql_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def safe_application_id(value: str) -> str | None:
    """Reject path traversal / namespace-colliding junk; allow registry-style ids."""
    import re

    text = value.strip()
    if not text or len(text) > 80:
        return None
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", text):
        return None
    return text


def _app_match_filter(app_id: str) -> str:
    """Exact label or URI local name ``app_<id>`` — never substring of namespace."""
    lit = _sparql_literal(app_id)
    local = _sparql_literal(f"app_{app_id}")
    return (
        f'LCASE(STR(?appLabel)) = LCASE("{lit}")'
        f' || STRENDS(LCASE(STR(?app)), "/{local}")'
        f' || STRENDS(LCASE(STR(?app)), "#{local}")'
    )


async def describe_application(
    store: AbstractGraphStore,
    application_id: str,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    interface_fallback: Any | None = None,
) -> dict[str, Any]:
    """Proxies, packages, topics, outbound routes for one application.

    Prefer SPARQL graph; if surface empty and ``interface_fallback`` is a
    RepoInterface (or callable returning one), use that.
    """
    app_id = safe_application_id(application_id)
    if not app_id:
        return {"error": "application_id required (alphanumeric / ._- only)"}
    app_filter = _app_match_filter(app_id)
    prefix = _prefix_block(namespace)

    # Separate queries — sibling OPTIONAL blocks would cartesian-product.
    keys_q = (
        prefix
        + f"""
SELECT ?appLabel ?conn ?url
WHERE {{
  GRAPH ?g {{
    ?app a lo:Application .
    OPTIONAL {{ ?app rdfs:label ?appLabel }}
    FILTER ({app_filter})
    OPTIONAL {{ ?app lo:connectionKey ?conn }}
    OPTIONAL {{ ?app lo:serviceUrlKey ?url }}
  }}
}}
"""
    )
    proxy_q = (
        prefix
        + f"""
SELECT ?pClass ?pBase ?pUrl
WHERE {{
  GRAPH ?g {{
    ?app a lo:Application .
    OPTIONAL {{ ?app rdfs:label ?appLabel }}
    FILTER ({app_filter})
    ?proxy a lo:ServiceProxy ; lo:belongsToApp ?app .
    OPTIONAL {{ ?proxy lo:proxyClass ?pClass }}
    OPTIONAL {{ ?proxy lo:proxyBase ?pBase }}
    OPTIONAL {{ ?proxy lo:serviceUrlKey ?pUrl }}
  }}
}}
"""
    )
    pkg_q = (
        prefix
        + f"""
SELECT ?pkgId ?pkgVer
WHERE {{
  GRAPH ?g {{
    ?app a lo:Application .
    OPTIONAL {{ ?app rdfs:label ?appLabel }}
    FILTER ({app_filter})
    ?pkg a lo:SdkPackage ; lo:belongsToApp ?app .
    OPTIONAL {{ ?pkg lo:packageId ?pkgId }}
    OPTIONAL {{ ?pkg lo:version ?pkgVer }}
  }}
}}
"""
    )
    topic_q = (
        prefix
        + f"""
SELECT ?tName
WHERE {{
  GRAPH ?g {{
    ?app a lo:Application .
    OPTIONAL {{ ?app rdfs:label ?appLabel }}
    FILTER ({app_filter})
    ?topic a lo:EventTopic ; lo:belongsToApp ?app .
    OPTIONAL {{ ?topic lo:topicName ?tName }}
  }}
}}
"""
    )
    route_q = (
        prefix
        + f"""
SELECT ?rPath ?rCaller ?rMethod ?rUrl
WHERE {{
  GRAPH ?g {{
    ?app a lo:Application .
    OPTIONAL {{ ?app rdfs:label ?appLabel }}
    FILTER ({app_filter})
    ?route a lo:RouteComposition ; lo:belongsToApp ?app .
    OPTIONAL {{ ?route lo:composedPath ?rPath }}
    OPTIONAL {{ ?route lo:callerSymbol ?rCaller }}
    OPTIONAL {{ ?route lo:httpMethod ?rMethod }}
    OPTIONAL {{ ?route lo:serviceUrlKey ?rUrl }}
  }}
}}
"""
    )
    try:
        keys_data = await _traced_query(store, keys_q, operation="describe_application.keys")
        proxy_data = await _traced_query(store, proxy_q, operation="describe_application.proxies")
        pkg_data = await _traced_query(store, pkg_q, operation="describe_application.packages")
        topic_data = await _traced_query(store, topic_q, operation="describe_application.topics")
        route_data = await _traced_query(store, route_q, operation="describe_application.routes")
    except GraphStoreError:
        raise

    connection_keys: list[str] = []
    service_url_keys: list[str] = []
    app_label = app_id
    for row in keys_data.get("results", {}).get("bindings", []):
        lab = _binding_str(row, "appLabel")
        if lab:
            app_label = lab
        conn = _binding_str(row, "conn")
        if conn and conn not in connection_keys:
            connection_keys.append(conn)
        url = _binding_str(row, "url")
        if url and url not in service_url_keys:
            service_url_keys.append(url)

    proxies: list[dict[str, Any]] = []
    seen_proxy: set[str] = set()
    for row in proxy_data.get("results", {}).get("bindings", []):
        p_class = _binding_str(row, "pClass")
        if p_class and p_class.lower() not in seen_proxy:
            seen_proxy.add(p_class.lower())
            proxies.append(
                {
                    "class": p_class,
                    "base": _binding_str(row, "pBase"),
                    "url_key": _binding_str(row, "pUrl"),
                }
            )

    packages: list[dict[str, Any]] = []
    seen_pkg: set[str] = set()
    for row in pkg_data.get("results", {}).get("bindings", []):
        pkg_id = _binding_str(row, "pkgId")
        if pkg_id and pkg_id.lower() not in seen_pkg:
            seen_pkg.add(pkg_id.lower())
            packages.append(
                {"package_id": pkg_id, "version": _binding_str(row, "pkgVer")}
            )

    topics: list[dict[str, Any]] = []
    seen_topic: set[str] = set()
    for row in topic_data.get("results", {}).get("bindings", []):
        t_name = _binding_str(row, "tName")
        if t_name and t_name.lower() not in seen_topic:
            seen_topic.add(t_name.lower())
            topics.append({"name": t_name, "role": None})

    routes: list[dict[str, Any]] = []
    seen_route: set[str] = set()
    for row in route_data.get("results", {}).get("bindings", []):
        r_path = _binding_str(row, "rPath")
        r_caller = _binding_str(row, "rCaller")
        r_key = f"{r_caller}|{r_path}".lower()
        if r_key != "|" and r_key not in seen_route:
            seen_route.add(r_key)
            routes.append(
                {
                    "path": r_path,
                    "caller": r_caller,
                    "method": _binding_str(row, "rMethod"),
                    "url_key": _binding_str(row, "rUrl"),
                }
            )

    result: dict[str, Any] = {
        "application_id": app_label,
        "source": "graph",
        "proxies": proxies,
        "packages": packages,
        "topics": topics,
        "connection_keys": connection_keys,
        "service_url_keys": service_url_keys,
        "route_compositions": routes,
    }
    surface = (
        proxies or packages or topics or routes or connection_keys or service_url_keys
    )
    if surface:
        return result

    iface = interface_fallback
    if callable(iface):
        iface = iface()
    if iface is not None and hasattr(iface, "proxies"):
        return _describe_from_interface(iface, application_id=app_id)
    return {
        **result,
        "note": "no interface surface in graph; re-index or provide interface.json",
    }
