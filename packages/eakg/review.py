"""Human review CLI helpers — append-only decision log."""

from __future__ import annotations

from typing import Any

from rdflib import Graph, Literal
from rdflib.namespace import RDF

from packages.capability_kg.ontology import (
    CLASS_CAPABILITY,
    CLASS_CROSS_APP_RELATIONSHIP,
    DEFAULT_NAMESPACE,
    PRED_REVIEW_STATUS,
    loanops_ns,
)
from packages.capability_kg.store import load_graph, save_graph
from packages.eakg.models import utc_now_iso
from packages.eakg.store import ShardStore


def list_pending(store: ShardStore, repository_id: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    ids = [repository_id] if repository_id else [
        p.stem for p in store.proposals_root.glob("*.jsonl")
    ]
    for rid in ids:
        if not rid:
            continue
        for row in store.read_proposals(rid):
            if str(row.get("status") or "") == "pending_review":
                out.append(row)
    return out


def decide(
    store: ShardStore,
    *,
    proposal_id: str,
    decision: str,
    reviewer: str = "human",
    note: str = "",
) -> dict[str, Any]:
    if decision not in {"approved", "rejected"}:
        raise ValueError("decision must be approved|rejected")
    row = {
        "proposal_id": proposal_id,
        "decision": decision,
        "reviewer": reviewer,
        "note": note,
        "decided_at": utc_now_iso(),
    }
    store.append_decision(row)
    # update proposal status in a side index file (append superseding row)
    for path in store.proposals_root.glob("*.jsonl"):
        rows = []
        changed = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            import json

            item = json.loads(line)
            if item.get("proposal_id") == proposal_id:
                item["status"] = decision
                changed = True
            rows.append(item)
        if changed:
            path.write_text(
                "\n".join(json.dumps(r) for r in rows) + "\n",
                encoding="utf-8",
            )
    return row


def auto_approve_structural(
    store: ShardStore,
    *,
    confidence_threshold: float = 1.0,
) -> int:
    """Mark high-confidence structural cross-app edges as approved in cross_app.ttl."""
    path = store.enterprise_root / "cross_app.ttl"
    if not path.is_file():
        return 0
    g = load_graph(path, namespace=DEFAULT_NAMESPACE)
    ns = loanops_ns(DEFAULT_NAMESPACE)
    count = 0
    for s, _, _ in g.triples((None, RDF.type, ns[CLASS_CROSS_APP_RELATIONSHIP])):
        conf = None
        for _, _, o in g.triples((s, ns["confidence"], None)):
            try:
                conf = float(o)
            except Exception:  # noqa: BLE001
                conf = None
        status = None
        for _, _, o in g.triples((s, ns[PRED_REVIEW_STATUS], None)):
            status = str(o)
        if conf is not None and conf >= confidence_threshold and status != "approved":
            g.set((s, ns[PRED_REVIEW_STATUS], Literal("approved")))
            count += 1
    if count:
        save_graph(g, path)
    return count


_HIGH_VALUE_KINDS = frozenset(
    {
        "consumesSdk",
        "sharesDto",
        "authenticatesVia",
        "publishesEvent",
        "readsDataStore",
        "callsApplication",
    }
)
_PILOT_APPS = frozenset({"escrow", "fees", "loanservices", "app_escrow", "app_fees", "app_loanservices"})


def _app_tail(uri_or_label: str) -> str:
    return uri_or_label.rsplit("/", 1)[-1].lower().removeprefix("app_")


def review_pilot_edges(
    store: ShardStore,
    *,
    reviewer: str = "pilot_review",
    reject_noisy_calls_operation: bool = True,
    approve_high_value_min_confidence: float = 0.9,
) -> dict[str, int]:
    """Approve high-value pilot edges; reject low-confidence callsOperation noise."""
    from packages.capability_kg.ontology import (
        PRED_CONFIDENCE,
        PRED_FROM_APP,
        PRED_RELATIONSHIP_KIND,
        PRED_TO_APP,
        PRED_TO_OPERATION,
        PRED_TO_PACKAGE,
    )

    path = store.enterprise_root / "cross_app.ttl"
    if not path.is_file():
        return {"approved": 0, "rejected": 0}

    g = load_graph(path, namespace=DEFAULT_NAMESPACE)
    ns = loanops_ns(DEFAULT_NAMESPACE)
    approved = 0
    rejected = 0

    for s, _, _ in list(g.triples((None, RDF.type, ns[CLASS_CROSS_APP_RELATIONSHIP]))):
        kind = str(next(g.objects(s, ns[PRED_RELATIONSHIP_KIND]), "") or "")
        status = str(next(g.objects(s, ns[PRED_REVIEW_STATUS]), "") or "")
        try:
            conf = float(next(g.objects(s, ns[PRED_CONFIDENCE]), 0) or 0)
        except Exception:  # noqa: BLE001
            conf = 0.0
        fr = _app_tail(str(next(g.objects(s, ns[PRED_FROM_APP]), "") or ""))
        to = _app_tail(str(next(g.objects(s, ns[PRED_TO_APP]), "") or ""))
        to_op = str(next(g.objects(s, ns[PRED_TO_OPERATION]), "") or "")
        to_pkg = str(next(g.objects(s, ns[PRED_TO_PACKAGE]), "") or "")

        # Reject noisy fuzzy operation matches (path "/") or EscrowDisbursement false positives
        if (
            reject_noisy_calls_operation
            and kind == "callsOperation"
            and status == "pending_review"
            and (
                conf < 0.85
                or "/:" in to_op
                or to_op.startswith("GET:/:")
                or "EscrowDisbursementTransactionsController" in to_op
            )
        ):
            g.set((s, ns[PRED_REVIEW_STATUS], Literal("rejected")))
            store.append_decision(
                {
                    "relationship": str(s),
                    "kind": kind,
                    "decision": "rejected",
                    "reviewer": reviewer,
                    "note": f"noisy callsOperation conf={conf} op={to_op[:120]}",
                    "decided_at": utc_now_iso(),
                }
            )
            rejected += 1
            continue

        # Approve high-value structural edges among pilot apps (or SDK packages)
        pilotish = fr in _PILOT_APPS or to in _PILOT_APPS or "LoanServices" in to_pkg
        if (
            kind in _HIGH_VALUE_KINDS
            and status in {"discovered", "pending_review", ""}
            and conf >= approve_high_value_min_confidence
            and pilotish
        ):
            g.set((s, ns[PRED_REVIEW_STATUS], Literal("approved")))
            store.append_decision(
                {
                    "relationship": str(s),
                    "kind": kind,
                    "decision": "approved",
                    "reviewer": reviewer,
                    "note": f"{fr}->{to} {to_pkg or to_op}",
                    "decided_at": utc_now_iso(),
                }
            )
            approved += 1

    if approved or rejected:
        save_graph(g, path)
    return {"approved": approved, "rejected": rejected}


def publish_approved_catalog(store: ShardStore, *, namespace: str = DEFAULT_NAMESPACE) -> int:
    """Union of capabilities with approved/published status into catalog/approved.ttl."""
    from packages.eakg.merge import merge_shards

    cg = merge_shards(store.root, namespace=namespace)
    ns = loanops_ns(namespace)
    out = Graph()
    out.bind("loanops", ns)
    for s, _, _ in cg.triples((None, RDF.type, ns[CLASS_CAPABILITY])):
        status = None
        for _, _, o in cg.triples((s, ns[PRED_REVIEW_STATUS], None)):
            status = str(o).lower()
        if status in {"approved", "published"}:
            for triple in cg.triples((s, None, None)):
                out.add(triple)
    # also include approved relationships
    for s, _, _ in cg.triples((None, RDF.type, ns[CLASS_CROSS_APP_RELATIONSHIP])):
        status = None
        for _, _, o in cg.triples((s, ns[PRED_REVIEW_STATUS], None)):
            status = str(o).lower()
        if status in {"approved", "published"}:
            for triple in cg.triples((s, None, None)):
                out.add(triple)
    store.write_approved(out)
    return len(out)


def audit_stale_proposals(store: ShardStore, *, stale_days: int = 14) -> list[dict[str, Any]]:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    stale: list[dict[str, Any]] = []
    for row in list_pending(store):
        created = str(row.get("created_at") or "")
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except ValueError:
            continue
        age = (now - dt).days
        if age >= stale_days:
            stale.append({**row, "age_days": age})
    return stale
