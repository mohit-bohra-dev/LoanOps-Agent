"""Serialize extractor facts + relationships into RDF graphs."""

from __future__ import annotations

import re
from typing import Any

from packages.capability_kg.ontology import (
    CLASS_API_OPERATION,
    CLASS_APPLICATION,
    CLASS_CAPABILITY,
    CLASS_CODE_UNIT,
    CLASS_CROSS_APP_RELATIONSHIP,
    CLASS_EVENT_TOPIC,
    CLASS_EVIDENCE,
    CLASS_REPOSITORY,
    CLASS_ROUTE_COMPOSITION,
    CLASS_SDK_PACKAGE,
    CLASS_SERVICE_PROXY,
    DEFAULT_NAMESPACE,
    PRED_AUTHZ_SOURCE,
    PRED_BELONGS_TO_APP,
    PRED_BELONGS_TO_REPO,
    PRED_CALLER_SYMBOL,
    PRED_COMMIT_SHA,
    PRED_COMPOSED_PATH,
    PRED_CONFIDENCE,
    PRED_CONN_KEY,
    PRED_DETECTOR_ID,
    PRED_DETECTOR_VERSION,
    PRED_EXTRACTED_AT,
    PRED_FILE_PATH,
    PRED_FROM_APP,
    PRED_HAS_EVIDENCE,
    PRED_HOSTS,
    PRED_HTTP_METHOD,
    PRED_HTTP_PATH,
    PRED_IMPLEMENTED_BY,
    PRED_IMPLEMENTED_BY_CODE_UNIT,
    PRED_INTENT,
    PRED_LINE_END,
    PRED_LINE_START,
    PRED_OPERATION_ID,
    PRED_PACKAGE_ID,
    PRED_PROXY_BASE,
    PRED_PROXY_CLASS,
    PRED_READ_ONLY,
    PRED_RELATIONSHIP_KIND,
    PRED_REPO_ID,
    PRED_REQUIRES_PERMISSION,
    PRED_REVIEW_STATUS,
    PRED_SERVICE_URL_KEY,
    PRED_SOURCE,
    PRED_TO_APP,
    PRED_TO_AUTH,
    PRED_TO_DATASTORE,
    PRED_TO_OPERATION,
    PRED_TO_PACKAGE,
    PRED_TO_TOPIC,
    PRED_TOPIC_NAME,
    PRED_VERSION,
    loanops_ns,
)
from packages.eakg.models import (
    ApiOperationFact,
    AuthzSource,
    CrossAppRelationship,
    Evidence,
    RepoInterface,
)
from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS, XSD


def _safe(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_")[:140]


_AUTHZ: dict[str, AuthzSource] = {
    "attribute": "attribute",
    "class-level": "class-level",
    "convention": "convention",
    "unknown": "unknown",
}


def _authz_source(raw: object) -> AuthzSource:
    if isinstance(raw, str) and raw in _AUTHZ:
        return _AUTHZ[raw]
    return "unknown"


def evidence_to_graph(items: list[Evidence], *, namespace: str = DEFAULT_NAMESPACE) -> Graph:
    ns = loanops_ns(namespace)
    g = Graph()
    g.bind("loanops", ns)
    for i, ev in enumerate(items):
        uri = ns[f"evidence_{_safe(ev.repository_id)}_{_safe(ev.detector_id)}_{i}_{ev.line_start}"]
        g.add((uri, RDF.type, ns[CLASS_EVIDENCE]))
        g.add((uri, ns[PRED_REPO_ID], Literal(ev.repository_id)))
        g.add((uri, ns[PRED_COMMIT_SHA], Literal(ev.commit_sha)))
        g.add((uri, ns[PRED_FILE_PATH], Literal(ev.file_path)))
        g.add((uri, ns[PRED_LINE_START], Literal(ev.line_start, datatype=XSD.integer)))
        g.add((uri, ns[PRED_LINE_END], Literal(ev.line_end, datatype=XSD.integer)))
        g.add((uri, ns[PRED_DETECTOR_ID], Literal(ev.detector_id)))
        g.add((uri, ns[PRED_DETECTOR_VERSION], Literal(ev.detector_version)))
        g.add((uri, ns[PRED_CONFIDENCE], Literal(ev.confidence, datatype=XSD.decimal)))
        g.add((uri, ns[PRED_EXTRACTED_AT], Literal(ev.extracted_at)))
    return g


def interface_to_graph(
    iface: RepoInterface,
    operations: list[ApiOperationFact] | None = None,
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> tuple[Graph, Graph]:
    """Return (graph.ttl facts, evidence.ttl)."""
    ns = loanops_ns(namespace)
    g = Graph()
    eg = Graph()
    g.bind("loanops", ns)
    eg.bind("loanops", ns)

    repo = ns[f"repo_{_safe(iface.repository_id)}"]
    g.add((repo, RDF.type, ns[CLASS_REPOSITORY]))
    g.add((repo, RDFS.label, Literal(iface.repository_id)))
    g.add((repo, ns[PRED_REPO_ID], Literal(iface.repository_id)))
    g.add((repo, ns[PRED_COMMIT_SHA], Literal(iface.commit_sha)))

    app = ns[f"app_{_safe(iface.application_id)}"]
    g.add((app, RDF.type, ns[CLASS_APPLICATION]))
    g.add((app, RDFS.label, Literal(iface.application_id)))
    g.add((app, ns[PRED_BELONGS_TO_REPO], repo))

    ops = operations or []
    if not ops:
        # rebuild light facts from interface JSON
        for o in iface.operations:
            summary_raw = o.get("summary")
            ops.append(
                ApiOperationFact(
                    operation_key=str(o.get("key") or ""),
                    http_method=str(o.get("method") or "GET"),
                    http_path=str(o.get("path") or "/"),
                    controller=str(o.get("controller") or ""),
                    action=str(o.get("action") or ""),
                    authz_policy=o.get("authz_policy")
                    if isinstance(o.get("authz_policy"), str)
                    else None,
                    authz_source=_authz_source(o.get("authz_source")),
                    read_only=bool(o.get("read_only", True)),
                    summary=str(summary_raw).strip() if isinstance(summary_raw, str) else None,
                )
            )

    ev_counter = 0
    for op in ops:
        op_id = op.action or op.operation_key
        op_uri = ns[f"op_{_safe(iface.application_id)}_{_safe(op_id)}_{_safe(op.http_method)}"]
        g.add((op_uri, RDF.type, ns[CLASS_API_OPERATION]))
        g.add((op_uri, ns[PRED_OPERATION_ID], Literal(op_id)))
        g.add((op_uri, ns[PRED_HTTP_METHOD], Literal(op.http_method)))
        g.add((op_uri, ns[PRED_HTTP_PATH], Literal(op.http_path)))
        g.add((op_uri, ns[PRED_BELONGS_TO_APP], app))
        g.add((op_uri, ns[PRED_AUTHZ_SOURCE], Literal(op.authz_source)))
        g.add((op_uri, ns[PRED_READ_ONLY], Literal(op.read_only, datatype=XSD.boolean)))
        if op.authz_policy:
            g.add((op_uri, ns[PRED_REQUIRES_PERMISSION], Literal(op.authz_policy)))
        if op.summary:
            g.add((op_uri, RDFS.comment, Literal(op.summary)))

        code = ns[f"code_{_safe(op.controller)}_{_safe(op.action)}"]
        g.add((code, RDF.type, ns[CLASS_CODE_UNIT]))
        g.add((code, RDFS.label, Literal(f"{op.controller}.{op.action}")))
        g.add((op_uri, ns[PRED_IMPLEMENTED_BY_CODE_UNIT], code))

        # Seed capability from operation (structural; review_status discovered)
        cap_name = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", op_id)
        cap_name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", cap_name).lower()
        cap = ns[f"cap_{_safe(iface.application_id)}_{_safe(cap_name)}"]
        comment = op.summary or f"Capability for {op_id}"
        g.add((cap, RDF.type, ns[CLASS_CAPABILITY]))
        g.add((cap, RDFS.label, Literal(cap_name)))
        g.add((cap, RDFS.comment, Literal(comment)))
        g.add((cap, ns[PRED_INTENT], Literal(comment)))
        g.add((cap, ns[PRED_IMPLEMENTED_BY], op_uri))
        g.add((cap, ns[PRED_BELONGS_TO_APP], app))
        g.add((cap, ns[PRED_REVIEW_STATUS], Literal("discovered")))
        g.add((cap, ns[PRED_SOURCE], Literal("static_dotnet")))
        g.add((cap, ns[PRED_READ_ONLY], Literal(op.read_only, datatype=XSD.boolean)))
        if op.authz_policy:
            g.add((cap, ns[PRED_REQUIRES_PERMISSION], Literal(op.authz_policy)))

        for ev in op.evidence:
            euri = ns[f"evidence_{_safe(iface.repository_id)}_{ev_counter}"]
            ev_counter += 1
            eg.add((euri, RDF.type, ns[CLASS_EVIDENCE]))
            eg.add((euri, ns[PRED_REPO_ID], Literal(ev.repository_id)))
            eg.add((euri, ns[PRED_COMMIT_SHA], Literal(ev.commit_sha)))
            eg.add((euri, ns[PRED_FILE_PATH], Literal(ev.file_path)))
            eg.add((euri, ns[PRED_LINE_START], Literal(ev.line_start, datatype=XSD.integer)))
            eg.add((euri, ns[PRED_LINE_END], Literal(ev.line_end, datatype=XSD.integer)))
            eg.add((euri, ns[PRED_DETECTOR_ID], Literal(ev.detector_id)))
            eg.add((euri, ns[PRED_DETECTOR_VERSION], Literal(ev.detector_version)))
            eg.add((euri, ns[PRED_CONFIDENCE], Literal(ev.confidence, datatype=XSD.decimal)))
            g.add((op_uri, ns[PRED_HAS_EVIDENCE], euri))
            g.add((cap, ns[PRED_HAS_EVIDENCE], euri))

    _materialize_interface_surface(g, ns, app, iface)

    return g, eg


_MAX_SURFACE_ITEMS = 200
_MAX_LITERAL = 240


def _bound_str(value: object, *, limit: int = _MAX_LITERAL) -> str:
    text = str(value or "").strip()
    return text[:limit] if text else ""


def _materialize_interface_surface(
    g: Graph,
    ns: Any,
    app: Any,
    iface: RepoInterface,
) -> None:
    """Write proxies / packages / topics / keys / outbound routes from interface JSON."""
    for key in iface.connection_keys[:_MAX_SURFACE_ITEMS]:
        lit = _bound_str(key)
        if lit:
            g.add((app, ns[PRED_CONN_KEY], Literal(lit)))
    for key in iface.service_url_keys[:_MAX_SURFACE_ITEMS]:
        lit = _bound_str(key)
        if lit:
            g.add((app, ns[PRED_SERVICE_URL_KEY], Literal(lit)))

    for i, pkg in enumerate(iface.packages[:_MAX_SURFACE_ITEMS]):
        if not isinstance(pkg, dict):
            continue
        pid = _bound_str(pkg.get("package_id") or pkg.get("id"))
        if not pid:
            continue
        puri = ns[f"pkg_{_safe(iface.application_id)}_{_safe(pid)}_{i}"]
        g.add((puri, RDF.type, ns[CLASS_SDK_PACKAGE]))
        g.add((puri, RDFS.label, Literal(pid)))
        g.add((puri, ns[PRED_PACKAGE_ID], Literal(pid)))
        ver = _bound_str(pkg.get("version"))
        if ver:
            g.add((puri, ns[PRED_VERSION], Literal(ver)))
        g.add((puri, ns[PRED_BELONGS_TO_APP], app))
        g.add((app, ns[PRED_HOSTS], puri))

    for i, topic in enumerate(iface.topics[:_MAX_SURFACE_ITEMS]):
        if not isinstance(topic, dict):
            continue
        name = _bound_str(topic.get("value") or topic.get("key") or topic.get("topic_name"))
        if not name:
            continue
        turi = ns[f"topic_{_safe(iface.application_id)}_{_safe(name)}_{i}"]
        g.add((turi, RDF.type, ns[CLASS_EVENT_TOPIC]))
        g.add((turi, RDFS.label, Literal(name)))
        g.add((turi, ns[PRED_TOPIC_NAME], Literal(name)))
        g.add((turi, ns[PRED_BELONGS_TO_APP], app))
        g.add((app, ns[PRED_HOSTS], turi))

    for i, proxy in enumerate(iface.proxies[:_MAX_SURFACE_ITEMS]):
        if not isinstance(proxy, dict):
            continue
        cls = _bound_str(proxy.get("class") or proxy.get("class_name"))
        if not cls:
            continue
        puri = ns[f"proxy_{_safe(iface.application_id)}_{_safe(cls)}_{i}"]
        g.add((puri, RDF.type, ns[CLASS_SERVICE_PROXY]))
        g.add((puri, RDFS.label, Literal(cls)))
        g.add((puri, ns[PRED_PROXY_CLASS], Literal(cls)))
        base = _bound_str(proxy.get("base") or proxy.get("base_class"))
        if base:
            g.add((puri, ns[PRED_PROXY_BASE], Literal(base)))
        url_key = _bound_str(proxy.get("url_key"))
        if url_key:
            g.add((puri, ns[PRED_SERVICE_URL_KEY], Literal(url_key)))
        g.add((puri, ns[PRED_BELONGS_TO_APP], app))
        g.add((app, ns[PRED_HOSTS], puri))

    for i, route in enumerate(iface.route_compositions[:_MAX_SURFACE_ITEMS]):
        if not isinstance(route, dict):
            continue
        path = _bound_str(route.get("path") or route.get("composed_path"))
        caller = _bound_str(route.get("caller") or route.get("caller_symbol"))
        if not path and not caller:
            continue
        ruri = ns[f"route_{_safe(iface.application_id)}_{i}_{_safe(path or caller)}"]
        g.add((ruri, RDF.type, ns[CLASS_ROUTE_COMPOSITION]))
        label = path or caller
        g.add((ruri, RDFS.label, Literal(label)))
        if path:
            g.add((ruri, ns[PRED_COMPOSED_PATH], Literal(path)))
        if caller:
            g.add((ruri, ns[PRED_CALLER_SYMBOL], Literal(caller)))
        method = _bound_str(route.get("method") or route.get("http_method"))
        if method:
            g.add((ruri, ns[PRED_HTTP_METHOD], Literal(method)))
        url_key = _bound_str(route.get("url_key"))
        if url_key:
            g.add((ruri, ns[PRED_SERVICE_URL_KEY], Literal(url_key)))
        g.add((ruri, ns[PRED_BELONGS_TO_APP], app))
        g.add((app, ns[PRED_HOSTS], ruri))


def relationships_to_graph(
    rels: list[CrossAppRelationship],
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> Graph:
    ns = loanops_ns(namespace)
    g = Graph()
    g.bind("loanops", ns)
    for rel in rels:
        if not rel.validate():
            continue
        uri = ns[rel.relationship_id]
        g.add((uri, RDF.type, ns[CLASS_CROSS_APP_RELATIONSHIP]))
        g.add((uri, ns[PRED_RELATIONSHIP_KIND], Literal(rel.kind)))
        g.add((uri, ns[PRED_FROM_APP], ns[f"app_{_safe(rel.from_application)}"]))
        g.add((uri, ns[PRED_TO_APP], ns[f"app_{_safe(rel.to_application)}"]))
        g.add((uri, ns[PRED_CONFIDENCE], Literal(rel.confidence, datatype=XSD.decimal)))
        g.add((uri, ns[PRED_REVIEW_STATUS], Literal(rel.review_status)))
        g.add((uri, ns[PRED_DETECTOR_ID], Literal(rel.detector_id)))
        g.add((uri, ns[PRED_DETECTOR_VERSION], Literal(rel.detector_version)))
        if rel.to_operation:
            g.add((uri, ns[PRED_TO_OPERATION], Literal(rel.to_operation)))
        if rel.to_package:
            g.add((uri, ns[PRED_TO_PACKAGE], Literal(rel.to_package)))
        if rel.to_topic:
            g.add((uri, ns[PRED_TO_TOPIC], Literal(rel.to_topic)))
        if rel.to_datastore:
            g.add((uri, ns[PRED_TO_DATASTORE], Literal(rel.to_datastore)))
        if rel.to_auth:
            g.add((uri, ns[PRED_TO_AUTH], Literal(rel.to_auth)))
        for i, ev in enumerate(rel.evidence):
            euri = ns[f"evidence_{rel.relationship_id}_{i}"]
            g.add((euri, RDF.type, ns[CLASS_EVIDENCE]))
            g.add((euri, ns[PRED_REPO_ID], Literal(ev.repository_id)))
            g.add((euri, ns[PRED_COMMIT_SHA], Literal(ev.commit_sha)))
            g.add((euri, ns[PRED_FILE_PATH], Literal(ev.file_path)))
            g.add((euri, ns[PRED_LINE_START], Literal(ev.line_start, datatype=XSD.integer)))
            g.add((euri, ns[PRED_LINE_END], Literal(ev.line_end, datatype=XSD.integer)))
            g.add((euri, ns[PRED_DETECTOR_ID], Literal(ev.detector_id)))
            g.add((euri, ns[PRED_DETECTOR_VERSION], Literal(ev.detector_version)))
            g.add((euri, ns[PRED_CONFIDENCE], Literal(ev.confidence, datatype=XSD.decimal)))
            g.add((euri, ns[PRED_EXTRACTED_AT], Literal(ev.extracted_at)))
            g.add((uri, ns[PRED_HAS_EVIDENCE], euri))
    return g


def enrich_operations_from_openapi(
    iface: RepoInterface,
    spec: dict[str, Any],
) -> RepoInterface:
    """Hybrid: attach OpenAPI operationId / summary onto matching path+method."""
    paths = spec.get("paths") or {}
    if not isinstance(paths, dict):
        return iface
    by_mp: dict[str, dict[str, Any]] = {}
    for path, item in paths.items():
        if not isinstance(item, dict):
            continue
        for method, op in item.items():
            if method.startswith("x-") or not isinstance(op, dict):
                continue
            by_mp[f"{method.upper()}:{path}"] = op
    new_ops: list[dict[str, Any]] = []
    for o in iface.operations:
        key = f"{o.get('method')}:{o.get('path')}"
        op = by_mp.get(key)
        row = dict(o)
        if op:
            if op.get("operationId"):
                row["openapi_operation_id"] = op["operationId"]
            bits: list[str] = []
            if isinstance(op.get("summary"), str) and op["summary"].strip():
                bits.append(op["summary"].strip())
            if isinstance(op.get("description"), str) and op["description"].strip():
                desc = op["description"].strip()
                if desc not in bits:
                    bits.append(desc)
            tags = op.get("tags")
            if isinstance(tags, list):
                tag_bits = [t.strip() for t in tags if isinstance(t, str) and t.strip()]
                if tag_bits:
                    bits.append("tags: " + ", ".join(tag_bits))
            if bits:
                row["summary"] = ". ".join(bits)
        new_ops.append(row)
    iface.operations = new_ops
    return iface
