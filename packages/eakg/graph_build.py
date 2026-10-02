"""Serialize extractor facts + relationships into RDF graphs."""

from __future__ import annotations

import re
from typing import Any

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from packages.capability_kg.ontology import (
    CLASS_API_OPERATION,
    CLASS_APPLICATION,
    CLASS_CAPABILITY,
    CLASS_CODE_UNIT,
    CLASS_CROSS_APP_RELATIONSHIP,
    CLASS_EVIDENCE,
    CLASS_REPOSITORY,
    DEFAULT_NAMESPACE,
    PRED_AUTHZ_SOURCE,
    PRED_BELONGS_TO_APP,
    PRED_BELONGS_TO_REPO,
    PRED_COMMIT_SHA,
    PRED_CONFIDENCE,
    PRED_DETECTOR_ID,
    PRED_DETECTOR_VERSION,
    PRED_EXTRACTED_AT,
    PRED_FILE_PATH,
    PRED_FROM_APP,
    PRED_HAS_EVIDENCE,
    PRED_HTTP_METHOD,
    PRED_HTTP_PATH,
    PRED_IMPLEMENTED_BY,
    PRED_IMPLEMENTED_BY_CODE_UNIT,
    PRED_LINE_END,
    PRED_LINE_START,
    PRED_OPERATION_ID,
    PRED_READ_ONLY,
    PRED_RELATIONSHIP_KIND,
    PRED_REPO_ID,
    PRED_REQUIRES_PERMISSION,
    PRED_REVIEW_STATUS,
    PRED_SOURCE,
    PRED_TO_APP,
    PRED_TO_AUTH,
    PRED_TO_DATASTORE,
    PRED_TO_OPERATION,
    PRED_TO_PACKAGE,
    PRED_TO_TOPIC,
    loanops_ns,
)
from packages.eakg.models import (
    ApiOperationFact,
    CrossAppRelationship,
    Evidence,
    RepoInterface,
)


def _safe(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_")[:140]


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
            ops.append(
                ApiOperationFact(
                    operation_key=str(o.get("key") or ""),
                    http_method=str(o.get("method") or "GET"),
                    http_path=str(o.get("path") or "/"),
                    controller=str(o.get("controller") or ""),
                    action=str(o.get("action") or ""),
                    authz_policy=o.get("authz_policy"),  # type: ignore[arg-type]
                    authz_source=o.get("authz_source") or "unknown",  # type: ignore[arg-type]
                    read_only=bool(o.get("read_only", True)),
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

        code = ns[f"code_{_safe(op.controller)}_{_safe(op.action)}"]
        g.add((code, RDF.type, ns[CLASS_CODE_UNIT]))
        g.add((code, RDFS.label, Literal(f"{op.controller}.{op.action}")))
        g.add((op_uri, ns[PRED_IMPLEMENTED_BY_CODE_UNIT], code))

        # Seed capability from operation (structural; review_status discovered)
        cap_name = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", op_id)
        cap_name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", cap_name).lower()
        cap = ns[f"cap_{_safe(iface.application_id)}_{_safe(cap_name)}"]
        g.add((cap, RDF.type, ns[CLASS_CAPABILITY]))
        g.add((cap, RDFS.label, Literal(cap_name)))
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

    return g, eg


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
            if op.get("summary"):
                row["summary"] = op["summary"]
        new_ops.append(row)
    iface.operations = new_ops
    return iface
