"""Build / load / manage process RDF graphs (ADR-028)."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from packages.capability_kg.ontology import (
    CLASS_BUSINESS_PROCESS,
    CLASS_BUSINESS_SYSTEM,
    CLASS_CAPABILITY,
    CLASS_CAPABILITY_LINK,
    CLASS_DOCUMENTATION,
    CLASS_PROCESS_STEP,
    CLASS_REGULATION,
    CLASS_TRANSITION,
    DEFAULT_NAMESPACE,
    PRED_DOCUMENTED_BY,
    PRED_EFFECTIVE_DATE,
    PRED_EXTRACTION_STATUS,
    PRED_EXTRACTOR_VERSION,
    PRED_FIRST_STEP,
    PRED_FROM_STEP,
    PRED_GOVERNED_BY,
    PRED_GUARD_LABEL,
    PRED_HAS_CAPABILITY_LINK,
    PRED_HAS_STEP,
    PRED_HAS_TRANSITION,
    PRED_LINK_STATUS,
    PRED_LINK_TYPE,
    PRED_LOST_FEATURES,
    PRED_MAPS_HASH,
    PRED_OPERATION_KEY,
    PRED_PROCEDURE_ID,
    PRED_REVIEW_STATUS,
    PRED_SOP_ROLE_LABEL,
    PRED_SOURCE,
    PRED_SOURCE_COMPLETENESS,
    PRED_SOURCE_HASH,
    PRED_SOURCE_ORDINAL,
    PRED_SOURCE_PAGE_ID,
    PRED_SOURCE_SECTION,
    PRED_SOURCE_STATUS,
    PRED_SOURCE_VERSION,
    PRED_STEP_KIND,
    PRED_SUB_PROCESS_OF,
    PRED_THRESHOLD_TEXT,
    PRED_THRESHOLD_UNIT,
    PRED_THRESHOLD_VALUE,
    PRED_TO_CAPABILITY,
    PRED_TO_STEP,
    PRED_TRANSITION_KIND,
    PRED_USES_SYSTEM,
    PRED_VALIDATION_STATUS,
    loanops_ns,
)
from packages.common.providers.graph_store import (
    AbstractGraphStore,
    named_graph_iri,
)
from packages.eakg.graph_upload import upload_graph
from packages.eakg.process_extract import (
    EXTRACTOR_VERSION,
    ProcessDraft,
    draft_to_dict,
    extract_from_paths,
    load_maps,
)
from packages.eakg.process_validate import ValidationResult, validate_process
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

PROCESS_NAMED_GRAPH_ID = "process_account_maintenance"


def _safe(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_")[:140]


def build_graph(
    drafts: list[ProcessDraft],
    validations: dict[str, ValidationResult],
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> Graph:
    ns = loanops_ns(namespace)
    g = Graph()
    g.bind("loanops", ns)
    for draft in drafts:
        _add_process(g, ns, draft, validations.get(draft.process_id))
    return g


def _add_process(
    g: Graph,
    ns: Any,
    draft: ProcessDraft,
    validation: ValidationResult | None,
) -> None:
    proc = ns[f"proc_{_safe(draft.process_id)}"]
    g.add((proc, RDF.type, ns[CLASS_BUSINESS_PROCESS]))
    g.add((proc, RDFS.label, Literal(draft.title[:120])))
    if draft.procedure_id:
        g.add((proc, ns[PRED_PROCEDURE_ID], Literal(draft.procedure_id)))
    if draft.effective_date:
        g.add((proc, ns[PRED_EFFECTIVE_DATE], Literal(draft.effective_date)))
    g.add((proc, ns[PRED_SOURCE_COMPLETENESS], Literal(draft.source_completeness)))
    g.add((proc, ns[PRED_EXTRACTION_STATUS], Literal(draft.extraction_status)))
    vstatus = validation.status if validation else "fail"
    g.add((proc, ns[PRED_VALIDATION_STATUS], Literal(vstatus)))
    g.add((proc, ns[PRED_REVIEW_STATUS], Literal("pending_review")))
    g.add((proc, ns[PRED_SOURCE_STATUS], Literal("current")))
    g.add((proc, ns[PRED_EXTRACTOR_VERSION], Literal(draft.extractor_version)))
    g.add((proc, ns[PRED_MAPS_HASH], Literal(draft.maps_hash)))
    g.add((proc, ns[PRED_SOURCE], Literal("process_rules")))

    doc = ns[f"doc_confluence_{_safe(draft.page_id)}"]
    g.add((doc, RDF.type, ns[CLASS_DOCUMENTATION]))
    g.add((doc, RDFS.label, Literal(f"confluence:{draft.page_id}")))
    g.add((doc, ns[PRED_SOURCE_PAGE_ID], Literal(draft.page_id)))
    g.add((doc, ns[PRED_SOURCE_VERSION], Literal(draft.source_version, datatype=XSD.integer)))
    g.add((doc, ns[PRED_SOURCE_HASH], Literal(draft.source_hash)))
    if draft.page_url:
        g.add((doc, RDFS.comment, Literal(draft.page_url[:240])))
    for feat in draft.lost_features:
        g.add((doc, ns[PRED_LOST_FEATURES], Literal(feat)))
    g.add((proc, ns[PRED_DOCUMENTED_BY], doc))

    for reg_id in draft.regulations:
        reg = ns[f"reg_{_safe(reg_id)}"]
        g.add((reg, RDF.type, ns[CLASS_REGULATION]))
        g.add((reg, RDFS.label, Literal(reg_id)))
        g.add((proc, ns[PRED_GOVERNED_BY], reg))

    for child in draft.children:
        child_uri = ns[f"proc_{_safe(child.process_id)}"]
        g.add((child_uri, RDF.type, ns[CLASS_BUSINESS_PROCESS]))
        g.add((child_uri, RDFS.label, Literal(child.title[:120])))
        g.add((child_uri, ns[PRED_EXTRACTION_STATUS], Literal("stub")))
        g.add((child_uri, ns[PRED_REVIEW_STATUS], Literal("pending_review")))
        g.add((child_uri, ns[PRED_SUB_PROCESS_OF], proc))
        cdoc = ns[f"doc_confluence_{_safe(child.page_id)}"]
        g.add((cdoc, RDF.type, ns[CLASS_DOCUMENTATION]))
        g.add((cdoc, ns[PRED_SOURCE_PAGE_ID], Literal(child.page_id)))
        g.add((child_uri, ns[PRED_DOCUMENTED_BY], cdoc))

    first: URIRef | None = None
    for step in draft.steps:
        suri = ns[f"step_{_safe(step.id)}"]
        g.add((suri, RDF.type, ns[CLASS_PROCESS_STEP]))
        g.add((suri, RDFS.label, Literal(step.label)))
        g.add((suri, ns[PRED_STEP_KIND], Literal(step.kind)))
        g.add((suri, ns[PRED_SOURCE_SECTION], Literal(step.source_section)))
        g.add(
            (
                suri,
                ns[PRED_SOURCE_ORDINAL],
                Literal(step.source_ordinal, datatype=XSD.integer),
            )
        )
        g.add((suri, ns[PRED_DOCUMENTED_BY], doc))
        g.add((proc, ns[PRED_HAS_STEP], suri))
        if step.kind == "start" and first is None:
            first = suri
        if step.sop_role_label:
            g.add((suri, ns[PRED_SOP_ROLE_LABEL], Literal(step.sop_role_label)))
        for sys_id in step.systems:
            sys_uri = ns[f"sys_{_safe(sys_id)}"]
            g.add((sys_uri, RDF.type, ns[CLASS_BUSINESS_SYSTEM]))
            g.add((sys_uri, RDFS.label, Literal(sys_id)))
            g.add((suri, ns[PRED_USES_SYSTEM], sys_uri))
        for th in step.thresholds:
            g.add((suri, ns[PRED_THRESHOLD_TEXT], Literal(th.text)))
            g.add(
                (
                    suri,
                    ns[PRED_THRESHOLD_VALUE],
                    Literal(th.value, datatype=XSD.integer),
                )
            )
            g.add((suri, ns[PRED_THRESHOLD_UNIT], Literal(th.unit)))
        for idx, op_key in enumerate(step.capability_keys):
            link = ns[f"clink_{_safe(step.id)}_{idx}"]
            g.add((link, RDF.type, ns[CLASS_CAPABILITY_LINK]))
            g.add((link, ns[PRED_OPERATION_KEY], Literal(op_key)))
            g.add((link, ns[PRED_LINK_TYPE], Literal("invokes")))
            g.add((link, ns[PRED_LINK_STATUS], Literal("unverified")))
            g.add((link, ns[PRED_DOCUMENTED_BY], doc))
            # Best-effort capability URI from hint pattern; ASK validates later.
            cap_local = _capability_local_from_key(op_key)
            if cap_local:
                cap = ns[cap_local]
                g.add((cap, RDF.type, ns[CLASS_CAPABILITY]))
                g.add((link, ns[PRED_TO_CAPABILITY], cap))
            g.add((suri, ns[PRED_HAS_CAPABILITY_LINK], link))

    if first is not None:
        g.add((proc, ns[PRED_FIRST_STEP], first))

    for tr in draft.transitions:
        turi = ns[f"tr_{_safe(tr.id)}"]
        g.add((turi, RDF.type, ns[CLASS_TRANSITION]))
        g.add((turi, ns[PRED_FROM_STEP], ns[f"step_{_safe(tr.from_step)}"]))
        if tr.to_step:
            g.add((turi, ns[PRED_TO_STEP], ns[f"step_{_safe(tr.to_step)}"]))
        g.add((turi, ns[PRED_GUARD_LABEL], Literal(tr.guard_label)))
        g.add((turi, ns[PRED_TRANSITION_KIND], Literal(tr.kind)))
        g.add((turi, ns[PRED_SOURCE_SECTION], Literal(tr.source_section)))
        g.add(
            (
                turi,
                ns[PRED_SOURCE_ORDINAL],
                Literal(tr.source_ordinal, datatype=XSD.integer),
            )
        )
        g.add((turi, ns[PRED_DOCUMENTED_BY], doc))
        g.add(
            (
                ns[f"step_{_safe(tr.from_step)}"],
                ns[PRED_HAS_TRANSITION],
                turi,
            )
        )


def _capability_local_from_key(op_key: str) -> str | None:
    """Derive seed-style cap local name from application|METHOD|path."""
    parts = op_key.split("|")
    if len(parts) != 3:
        return None
    app, _method, path = parts
    # Last path segment as action-ish name.
    action = path.rstrip("/").split("/")[-1]
    if not action:
        return None
    snake = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", action)
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", snake).lower()
    snake = re.sub(r"[^a-z0-9_]+", "_", snake).strip("_")
    return f"cap_{_safe(app)}_{_safe(snake)}"


async def load_processes(
    store: AbstractGraphStore,
    drafts: list[ProcessDraft],
    validations: dict[str, ValidationResult],
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> dict[str, Any]:
    g = build_graph(drafts, validations, namespace=namespace)
    iri = await upload_graph(
        store, PROCESS_NAMED_GRAPH_ID, g, namespace=namespace
    )
    return {
        "named_graph": iri,
        "triples": len(g),
        "processes": [d.process_id for d in drafts],
        "review_status": "pending_review",
    }


async def set_review_status(
    store: AbstractGraphStore,
    process_id: str,
    status: str,
    *,
    reviewer: str = "",
    namespace: str = DEFAULT_NAMESPACE,
) -> dict[str, Any]:
    """Flip hasReviewStatus. Pilot may leave pending_review unused."""
    ns = loanops_ns(namespace)
    proc = f"{ns}proc_{_safe(process_id)}"
    graph_iri = named_graph_iri(PROCESS_NAMED_GRAPH_ID, namespace=namespace)
    update = f"""
    PREFIX loanops: <{ns}>
    DELETE {{ GRAPH <{graph_iri}> {{ <{proc}> loanops:hasReviewStatus ?old }} }}
    INSERT {{ GRAPH <{graph_iri}> {{
      <{proc}> loanops:hasReviewStatus "{status}" .
      {f'<{proc}> loanops:reviewedBy "{reviewer}" .' if reviewer else ''}
    }} }}
    WHERE {{ GRAPH <{graph_iri}> {{ OPTIONAL {{ <{proc}> loanops:hasReviewStatus ?old }} }} }}
    """
    await store.update(update)
    return {"process_id": process_id, "hasReviewStatus": status, "reviewer": reviewer}


async def verify_fresh(
    store: AbstractGraphStore,
    process_id: str,
    *,
    live_version: int,
    live_hash: str,
    namespace: str = DEFAULT_NAMESPACE,
) -> dict[str, Any]:
    ns = loanops_ns(namespace)
    graph_iri = named_graph_iri(PROCESS_NAMED_GRAPH_ID, namespace=namespace)
    proc = f"{ns}proc_{_safe(process_id)}"
    ask = f"""
    PREFIX loanops: <{ns}>
    ASK {{
      GRAPH <{graph_iri}> {{
        <{proc}> loanops:documentedBy ?doc .
        ?doc loanops:sourceVersion ?v .
        ?doc loanops:sourceHash ?h .
        FILTER(xsd:integer(?v) = {int(live_version)} && str(?h) = "{live_hash}")
      }}
    }}
    """
    # RDFLib FakeGraphStore may not bind xsd; use SELECT instead.
    q = f"""
    PREFIX loanops: <{ns}>
    SELECT ?v ?h WHERE {{
      GRAPH <{graph_iri}> {{
        <{proc}> loanops:documentedBy ?doc .
        ?doc loanops:sourceVersion ?v .
        ?doc loanops:sourceHash ?h .
      }}
    }}
    """
    result = await store.query(q)
    bindings = result.get("results", {}).get("bindings", [])
    stale = True
    if bindings:
        v = bindings[0].get("v", {}).get("value")
        h = bindings[0].get("h", {}).get("value")
        stale = not (str(v) == str(live_version) and h == live_hash)
    if stale:
        update = f"""
        PREFIX loanops: <{ns}>
        DELETE {{ GRAPH <{graph_iri}> {{
          <{proc}> loanops:sourceStatus ?s .
          <{proc}> loanops:hasReviewStatus ?r .
        }} }}
        INSERT {{ GRAPH <{graph_iri}> {{
          <{proc}> loanops:sourceStatus "stale" .
          <{proc}> loanops:hasReviewStatus "needs_reapproval" .
        }} }}
        WHERE {{ GRAPH <{graph_iri}> {{
          OPTIONAL {{ <{proc}> loanops:sourceStatus ?s }}
          OPTIONAL {{ <{proc}> loanops:hasReviewStatus ?r }}
        }} }}
        """
        await store.update(update)
    _ = ask
    return {"process_id": process_id, "stale": stale}


async def revalidate_links(
    store: AbstractGraphStore,
    *,
    known_operation_keys: set[str],
    namespace: str = DEFAULT_NAMESPACE,
) -> dict[str, Any]:
    """Flag capability links whose operation_key is missing from known set."""
    ns = loanops_ns(namespace)
    graph_iri = named_graph_iri(PROCESS_NAMED_GRAPH_ID, namespace=namespace)
    q = f"""
    PREFIX loanops: <{ns}>
    SELECT ?link ?key ?proc WHERE {{
      GRAPH <{graph_iri}> {{
        ?link a loanops:CapabilityLink ;
              loanops:operationKey ?key .
        ?step loanops:hasCapabilityLink ?link .
        ?proc loanops:hasStep ?step .
      }}
    }}
    """
    result = await store.query(q)
    broken: list[dict[str, str]] = []
    for row in result.get("results", {}).get("bindings", []):
        key = row.get("key", {}).get("value", "")
        link = row.get("link", {}).get("value", "")
        proc = row.get("proc", {}).get("value", "")
        if key not in known_operation_keys:
            broken.append({"link": link, "operation_key": key, "process": proc})
            update = f"""
            PREFIX loanops: <{ns}>
            DELETE {{ GRAPH <{graph_iri}> {{
              <{link}> loanops:linkStatus ?old .
              <{proc}> loanops:hasReviewStatus ?r .
            }} }}
            INSERT {{ GRAPH <{graph_iri}> {{
              <{link}> loanops:linkStatus "broken" .
              <{proc}> loanops:hasReviewStatus "needs_reapproval" .
            }} }}
            WHERE {{ GRAPH <{graph_iri}> {{
              OPTIONAL {{ <{link}> loanops:linkStatus ?old }}
              OPTIONAL {{ <{proc}> loanops:hasReviewStatus ?r }}
            }} }}
            """
            await store.update(update)
    return {"broken_count": len(broken), "broken": broken}


async def explain_process(
    store: AbstractGraphStore,
    process_id: str,
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> dict[str, Any]:
    ns = loanops_ns(namespace)
    graph_iri = named_graph_iri(PROCESS_NAMED_GRAPH_ID, namespace=namespace)
    proc = f"{ns}proc_{_safe(process_id)}"
    q = f"""
    PREFIX loanops: <{ns}>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?label ?procId ?extract ?review ?sourceComp ?val ?sourceStatus
           ?step ?stepLabel ?stepKind ?ord
    WHERE {{
      GRAPH <{graph_iri}> {{
        <{proc}> rdfs:label ?label .
        OPTIONAL {{ <{proc}> loanops:procedureId ?procId }}
        OPTIONAL {{ <{proc}> loanops:extractionStatus ?extract }}
        OPTIONAL {{ <{proc}> loanops:hasReviewStatus ?review }}
        OPTIONAL {{ <{proc}> loanops:sourceCompleteness ?sourceComp }}
        OPTIONAL {{ <{proc}> loanops:validationStatus ?val }}
        OPTIONAL {{ <{proc}> loanops:sourceStatus ?sourceStatus }}
        OPTIONAL {{
          <{proc}> loanops:hasStep ?step .
          ?step rdfs:label ?stepLabel ;
                loanops:stepKind ?stepKind ;
                loanops:sourceOrdinal ?ord .
        }}
      }}
    }}
    ORDER BY ?ord
    """
    result = await store.query(q)
    steps: list[dict[str, Any]] = []
    meta: dict[str, Any] = {"process_id": process_id}
    for row in result.get("results", {}).get("bindings", []):
        for k in ("label", "procId", "extract", "review", "sourceComp", "val", "sourceStatus"):
            if k in row and k not in meta:
                meta[k] = row[k].get("value")
        if "step" in row:
            steps.append(
                {
                    "id": row["step"]["value"],
                    "label": row.get("stepLabel", {}).get("value"),
                    "kind": row.get("stepKind", {}).get("value"),
                    "ordinal": row.get("ord", {}).get("value"),
                }
            )
    meta["steps"] = steps
    return meta


def report_extraction(
    drafts: list[ProcessDraft],
    validations: dict[str, ValidationResult],
) -> dict[str, Any]:
    return {
        "extractor_version": EXTRACTOR_VERSION,
        "processes": [
            {
                "process_id": d.process_id,
                "procedure_id": d.procedure_id,
                "source_completeness": d.source_completeness,
                "lost_features": d.lost_features,
                "extraction_status": d.extraction_status,
                "needs_review_count": len(d.needs_review),
                "needs_review": [asdict(n) for n in d.needs_review],
                "step_count": len(d.steps),
                "transition_count": len(d.transitions),
                "child_stubs": len(d.children),
                "capability_keys": sorted(
                    {k for s in d.steps for k in s.capability_keys}
                ),
                "validation": {
                    "status": validations[d.process_id].status
                    if d.process_id in validations
                    else "missing",
                    "failures": validations[d.process_id].failures
                    if d.process_id in validations
                    else [],
                    "decision_sheet": [
                        asdict(r)
                        for r in (
                            validations[d.process_id].decision_sheet
                            if d.process_id in validations
                            else []
                        )
                    ],
                },
            }
            for d in drafts
        ],
    }


def extract_bundle(
    fixture_dir: Path,
    maps_dir: Path,
    names: list[str],
) -> tuple[list[ProcessDraft], dict[str, ValidationResult]]:
    drafts: list[ProcessDraft] = []
    validations: dict[str, ValidationResult] = {}
    for name in names:
        md = fixture_dir / f"{name}.md"
        meta = fixture_dir / f"{name}.meta.json"
        draft = extract_from_paths(md, meta, maps_dir)
        drafts.append(draft)
        validations[draft.process_id] = validate_process(draft)
    return drafts, validations


def write_proposal(
    path: Path,
    drafts: list[ProcessDraft],
    validations: dict[str, ValidationResult],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "1.0.0",
        "review_status": "pending_review",
        "report": report_extraction(drafts, validations),
        "processes": [draft_to_dict(d) for d in drafts],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def default_fixture_names() -> list[str]:
    return [
        "account_maintenance",
        "efta_sensitive",
        "efta_paid_in_advance",
        "fha_non_impound",
    ]


def maps_dir_default() -> Path:
    return Path("data/process_kg/maps")


# Re-export for CLI convenience
__all__ = [
    "PROCESS_NAMED_GRAPH_ID",
    "build_graph",
    "load_processes",
    "set_review_status",
    "verify_fresh",
    "revalidate_links",
    "explain_process",
    "report_extraction",
    "extract_bundle",
    "write_proposal",
    "default_fixture_names",
    "maps_dir_default",
    "load_maps",
]
