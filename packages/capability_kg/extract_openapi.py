"""OpenAPI → RDF capability extraction (offline)."""

from __future__ import annotations

import re
from typing import Any

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from packages.capability_kg.ontology import (
    CLASS_API_OPERATION,
    CLASS_APPLICATION,
    CLASS_CAPABILITY,
    CLASS_DOMAIN,
    CLASS_MCP_SERVER,
    CLASS_PERMISSION,
    DEFAULT_NAMESPACE,
    PRED_BELONGS_TO_APP,
    PRED_EXPOSED_BY,
    PRED_HAS_DOMAIN,
    PRED_HTTP_METHOD,
    PRED_HTTP_PATH,
    PRED_IMPLEMENTED_BY,
    PRED_INTENT,
    PRED_OPERATION_ID,
    PRED_READ_ONLY,
    PRED_REQUIRES_PERMISSION,
    PRED_REVIEW_STATUS,
    PRED_SOURCE,
    PRED_VERSION,
    loanops_ns,
)
from packages.sse.types import ApiOperation

_WRITE_METHODS = frozenset({"post", "put", "patch", "delete"})


def camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def capability_id_for_operation(operation_id: str) -> str:
    return camel_to_snake(operation_id)


def _safe_local(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_")[:120]


def build_graph_from_operations(
    operations: list[ApiOperation],
    *,
    namespace: str = DEFAULT_NAMESPACE,
    mcp_server_id: str = "loanops",
    domain_label: str = "Loan Servicing",
    review_status: str = "discovered",
) -> Graph:
    """Materialize Application, APIOperation, Capability triples from OpenAPI ops."""
    ns = loanops_ns(namespace)
    graph = Graph()
    graph.bind("loanops", ns)
    graph.bind("rdfs", RDFS)

    domain = ns[f"domain_{_safe_local(domain_label.lower().replace(' ', '_'))}"]
    graph.add((domain, RDF.type, ns[CLASS_DOMAIN]))
    graph.add((domain, RDFS.label, Literal(domain_label)))

    mcp = ns[f"mcp_{_safe_local(mcp_server_id)}"]
    graph.add((mcp, RDF.type, ns[CLASS_MCP_SERVER]))
    graph.add((mcp, RDFS.label, Literal(mcp_server_id)))

    perm = ns["perm_loan_read"]
    graph.add((perm, RDF.type, ns[CLASS_PERMISSION]))
    graph.add((perm, RDFS.label, Literal("loan.read")))

    apps_seen: set[str] = set()

    for op in operations:
        app_key = op.source_id or "unknown"
        if app_key not in apps_seen:
            apps_seen.add(app_key)
            app = ns[f"app_{_safe_local(app_key)}"]
            graph.add((app, RDF.type, ns[CLASS_APPLICATION]))
            graph.add((app, RDFS.label, Literal(op.source_label or app_key)))

        op_local = op.operation_id or f"{op.method}_{_safe_local(op.path)}"
        op_uri = ns[f"op_{_safe_local(op_local)}"]
        app_uri = ns[f"app_{_safe_local(app_key)}"]
        graph.add((op_uri, RDF.type, ns[CLASS_API_OPERATION]))
        graph.add((op_uri, RDFS.label, Literal(op_local)))
        if op.summary:
            graph.add((op_uri, RDFS.comment, Literal(op.summary)))
        graph.add((op_uri, ns[PRED_OPERATION_ID], Literal(op_local)))
        graph.add((op_uri, ns[PRED_HTTP_METHOD], Literal(op.method.upper())))
        graph.add((op_uri, ns[PRED_HTTP_PATH], Literal(op.path)))
        graph.add((op_uri, ns[PRED_BELONGS_TO_APP], app_uri))

        if not op.operation_id:
            continue

        cap_name = capability_id_for_operation(op.operation_id)
        cap = ns[f"cap_{_safe_local(cap_name)}"]
        read_only = op.method.lower() not in _WRITE_METHODS and not op.has_request_body
        comment = op.summary or f"Capability for {op.operation_id}"
        graph.add((cap, RDF.type, ns[CLASS_CAPABILITY]))
        graph.add((cap, RDFS.label, Literal(cap_name)))
        graph.add((cap, RDFS.comment, Literal(comment)))
        graph.add((cap, ns[PRED_HAS_DOMAIN], domain))
        graph.add((cap, ns[PRED_IMPLEMENTED_BY], op_uri))
        graph.add((cap, ns[PRED_EXPOSED_BY], mcp))
        graph.add((cap, ns[PRED_REQUIRES_PERMISSION], perm))
        graph.add((cap, ns[PRED_READ_ONLY], Literal(read_only, datatype=XSD.boolean)))
        graph.add((cap, ns[PRED_REVIEW_STATUS], Literal(review_status)))
        graph.add((cap, ns[PRED_SOURCE], Literal("openapi")))
        graph.add((cap, ns[PRED_VERSION], Literal("0.1")))
        graph.add((cap, ns[PRED_INTENT], Literal(comment)))

    return graph


def build_graph_from_openapi_dict(
    raw: dict[str, Any],
    *,
    source_id: str = "loanservices",
    source_label: str = "LoanServices",
    source_base_url: str = "https://example.invalid",
    namespace: str = DEFAULT_NAMESPACE,
) -> Graph:
    """Parse a raw OpenAPI dict via packages.sse.catalog then build RDF."""
    from packages.sse.catalog import parse_openapi_document

    ops = parse_openapi_document(
        raw,
        source_id=source_id,
        source_label=source_label,
        fallback_base=source_base_url,
    )
    return build_graph_from_operations(ops, namespace=namespace)


def uri_to_str(node: URIRef | Any) -> str:
    return str(node)
