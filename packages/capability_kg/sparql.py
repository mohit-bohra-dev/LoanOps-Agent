"""Parameterized SPARQL helpers. Never concat raw user text into SPARQL."""

from __future__ import annotations

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS
from rdflib.plugins.sparql import prepareQuery

from packages.capability_kg.ontology import DEFAULT_NAMESPACE, loanops_ns


def _initns(namespace: str = DEFAULT_NAMESPACE) -> dict[str, object]:
    return {"loanops": loanops_ns(namespace), "rdf": RDF, "rdfs": RDFS}


_NS = _initns()

_Q_BY_LABEL_CONTAINS = prepareQuery(
    """
    SELECT ?capability ?label ?description ?operationId ?readOnly ?status ?permission
    WHERE {
      ?capability a loanops:Capability ;
                  rdfs:label ?label .
      OPTIONAL { ?capability rdfs:comment ?description }
      OPTIONAL { ?capability loanops:implementedBy ?op .
                 ?op loanops:operationId ?operationId }
      OPTIONAL { ?capability loanops:readOnly ?readOnly }
      OPTIONAL { ?capability loanops:hasReviewStatus ?status }
      OPTIONAL { ?capability loanops:requiresPermission ?perm .
                 ?perm rdfs:label ?permission }
      FILTER(CONTAINS(LCASE(STR(?label)), LCASE(?needle)))
    }
    """,
    initNs=_NS,
)

_Q_BY_COMMENT_CONTAINS = prepareQuery(
    """
    SELECT ?capability ?label ?description ?operationId ?readOnly ?status ?permission
    WHERE {
      ?capability a loanops:Capability ;
                  rdfs:label ?label .
      OPTIONAL { ?capability rdfs:comment ?description }
      OPTIONAL { ?capability loanops:implementedBy ?op .
                 ?op loanops:operationId ?operationId }
      OPTIONAL { ?capability loanops:readOnly ?readOnly }
      OPTIONAL { ?capability loanops:hasReviewStatus ?status }
      OPTIONAL { ?capability loanops:requiresPermission ?perm .
                 ?perm rdfs:label ?permission }
      FILTER(BOUND(?description) && CONTAINS(LCASE(STR(?description)), LCASE(?needle)))
    }
    """,
    initNs=_NS,
)

_Q_READ_ONLY = prepareQuery(
    """
    SELECT ?capability ?label ?description ?operationId ?readOnly ?status ?permission
    WHERE {
      ?capability a loanops:Capability ;
                  rdfs:label ?label ;
                  loanops:readOnly true .
      OPTIONAL { ?capability rdfs:comment ?description }
      OPTIONAL { ?capability loanops:implementedBy ?op .
                 ?op loanops:operationId ?operationId }
      OPTIONAL { ?capability loanops:hasReviewStatus ?status }
      OPTIONAL { ?capability loanops:requiresPermission ?perm .
                 ?perm rdfs:label ?permission }
      BIND(true AS ?readOnly)
    }
    """,
    initNs=_NS,
)

_Q_BY_PERMISSION = prepareQuery(
    """
    SELECT ?capability ?label ?description ?operationId ?readOnly ?status ?permission
    WHERE {
      ?capability a loanops:Capability ;
                  rdfs:label ?label ;
                  loanops:requiresPermission ?perm .
      ?perm rdfs:label ?permission .
      FILTER(LCASE(STR(?permission)) = LCASE(?permLabel))
      OPTIONAL { ?capability rdfs:comment ?description }
      OPTIONAL { ?capability loanops:implementedBy ?op .
                 ?op loanops:operationId ?operationId }
      OPTIONAL { ?capability loanops:readOnly ?readOnly }
      OPTIONAL { ?capability loanops:hasReviewStatus ?status }
    }
    """,
    initNs=_NS,
)

_Q_BY_DOMAIN = prepareQuery(
    """
    SELECT ?capability ?label ?description ?operationId ?readOnly ?status ?permission
    WHERE {
      ?capability a loanops:Capability ;
                  rdfs:label ?label ;
                  loanops:hasDomain ?domain .
      ?domain rdfs:label ?domainLabel .
      FILTER(LCASE(STR(?domainLabel)) = LCASE(?needle))
      OPTIONAL { ?capability rdfs:comment ?description }
      OPTIONAL { ?capability loanops:implementedBy ?op .
                 ?op loanops:operationId ?operationId }
      OPTIONAL { ?capability loanops:readOnly ?readOnly }
      OPTIONAL { ?capability loanops:hasReviewStatus ?status }
      OPTIONAL { ?capability loanops:requiresPermission ?perm .
                 ?perm rdfs:label ?permission }
    }
    """,
    initNs=_NS,
)

_Q_BY_APP = prepareQuery(
    """
    SELECT ?capability ?label ?description ?operationId ?readOnly ?status ?permission
    WHERE {
      ?capability a loanops:Capability ;
                  rdfs:label ?label ;
                  loanops:implementedBy ?op .
      ?op loanops:belongsToApp ?app .
      ?app rdfs:label ?appLabel .
      FILTER(LCASE(STR(?appLabel)) = LCASE(?needle))
      OPTIONAL { ?capability rdfs:comment ?description }
      OPTIONAL { ?op loanops:operationId ?operationId }
      OPTIONAL { ?capability loanops:readOnly ?readOnly }
      OPTIONAL { ?capability loanops:hasReviewStatus ?status }
      OPTIONAL { ?capability loanops:requiresPermission ?perm .
                 ?perm rdfs:label ?permission }
    }
    """,
    initNs=_NS,
)

_Q_GET_ONE = prepareQuery(
    """
    SELECT ?capability ?label ?description ?operationId ?readOnly ?status ?permission
    WHERE {
      ?capability a loanops:Capability ;
                  rdfs:label ?label .
      FILTER(LCASE(STR(?label)) = LCASE(?exact))
      OPTIONAL { ?capability rdfs:comment ?description }
      OPTIONAL { ?capability loanops:implementedBy ?op .
                 ?op loanops:operationId ?operationId }
      OPTIONAL { ?capability loanops:readOnly ?readOnly }
      OPTIONAL { ?capability loanops:hasReviewStatus ?status }
      OPTIONAL { ?capability loanops:requiresPermission ?perm .
                 ?perm rdfs:label ?permission }
    }
    """,
    initNs=_NS,
)

_Q_ALL = prepareQuery(
    """
    SELECT ?capability ?label ?description ?operationId ?readOnly ?status ?permission
    WHERE {
      ?capability a loanops:Capability ;
                  rdfs:label ?label .
      OPTIONAL { ?capability rdfs:comment ?description }
      OPTIONAL { ?capability loanops:implementedBy ?op .
                 ?op loanops:operationId ?operationId }
      OPTIONAL { ?capability loanops:readOnly ?readOnly }
      OPTIONAL { ?capability loanops:hasReviewStatus ?status }
      OPTIONAL { ?capability loanops:requiresPermission ?perm .
                 ?perm rdfs:label ?permission }
    }
    """,
    initNs=_NS,
)


def _row(binding: object) -> dict[str, str | bool | None]:
    def _get(name: str) -> object | None:
        try:
            val: object = binding[name]  # type: ignore[index]
            return val
        except Exception:  # noqa: BLE001
            return None

    read = _get("readOnly")
    read_bool: bool | None
    if read is None:
        read_bool = None
    else:
        read_bool = str(read).lower() in ("true", "1")

    uri = _get("capability")
    return {
        "uri": str(uri) if uri is not None else None,
        "id": str(_get("label") or ""),
        "description": str(_get("description")) if _get("description") is not None else None,
        "operation_id": str(_get("operationId")) if _get("operationId") is not None else None,
        "read_only": read_bool,
        "review_status": str(_get("status")) if _get("status") is not None else None,
        "permission": str(_get("permission")) if _get("permission") is not None else None,
    }


def _run(
    graph: Graph,
    query: object,
    *,
    namespace: str,
    bindings: dict[str, Literal | URIRef] | None = None,
) -> list[dict[str, str | bool | None]]:
    _ = namespace  # prepared queries use default ontology NS; custom NS → rebuild later
    rows = graph.query(query, initBindings=bindings or {})  # type: ignore[arg-type]
    return [_row(r) for r in rows]


def search_by_needle(
    graph: Graph,
    needle: str,
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> list[dict[str, str | bool | None]]:
    """Label or comment contains needle (bound as Literal — not string-concat SPARQL)."""
    lit = Literal(needle.strip())
    by_label = _run(graph, _Q_BY_LABEL_CONTAINS, namespace=namespace, bindings={"needle": lit})
    by_comment = _run(
        graph, _Q_BY_COMMENT_CONTAINS, namespace=namespace, bindings={"needle": lit}
    )
    seen: set[str] = set()
    out: list[dict[str, str | bool | None]] = []
    for row in by_label + by_comment:
        key = str(row.get("id") or row.get("uri") or "")
        if key and key not in seen:
            seen.add(key)
            out.append(row)
    return out


def list_read_only(
    graph: Graph, *, namespace: str = DEFAULT_NAMESPACE
) -> list[dict[str, str | bool | None]]:
    return _run(graph, _Q_READ_ONLY, namespace=namespace)


def by_permission(
    graph: Graph, permission: str, *, namespace: str = DEFAULT_NAMESPACE
) -> list[dict[str, str | bool | None]]:
    return _run(
        graph,
        _Q_BY_PERMISSION,
        namespace=namespace,
        bindings={"permLabel": Literal(permission)},
    )


def by_domain(
    graph: Graph, domain: str, *, namespace: str = DEFAULT_NAMESPACE
) -> list[dict[str, str | bool | None]]:
    return _run(
        graph,
        _Q_BY_DOMAIN,
        namespace=namespace,
        bindings={"needle": Literal(domain)},
    )


def by_application(
    graph: Graph, application: str, *, namespace: str = DEFAULT_NAMESPACE
) -> list[dict[str, str | bool | None]]:
    return _run(
        graph,
        _Q_BY_APP,
        namespace=namespace,
        bindings={"needle": Literal(application)},
    )


def get_by_id(
    graph: Graph, capability_id: str, *, namespace: str = DEFAULT_NAMESPACE
) -> dict[str, str | bool | None] | None:
    rows = _run(
        graph,
        _Q_GET_ONE,
        namespace=namespace,
        bindings={"exact": Literal(capability_id)},
    )
    return rows[0] if rows else None


def list_all(
    graph: Graph, *, namespace: str = DEFAULT_NAMESPACE
) -> list[dict[str, str | bool | None]]:
    return _run(graph, _Q_ALL, namespace=namespace)
