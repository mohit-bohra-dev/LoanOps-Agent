"""Validation gate for investigator proposals (ADR-029)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from packages.eakg.models import ApiOperationFact, CrossAppRelationship, Evidence

HTTP_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})
IMPLEMENTATION_DETECTORS = frozenset(
    {
        "dotnet_roslyn",
        "dotnet_static",
        "treesitter_python",
        "treesitter_node",
        "graphify_ast",
    }
)
GOVERNED_KINDS = frozenset(
    {
        "capability_link",
        "overlapsCapability",
        "callsOperation",
        "callsApplication",
    }
)

ProposalKind = Literal[
    "operation",
    "relationship",
    "process_step",
    "capability_link",
    "conflict_resolution",
    "pattern",
    "extractor_change",
    "no_finding",
]


@dataclass
class GateVerdict:
    accepted: bool
    reasons: list[str] = field(default_factory=list)
    tier: str = "candidate"  # candidate | rejected

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CandidateProposal:
    kind: ProposalKind
    repository_id: str
    ledger_item_id: str
    payload: dict[str, Any]
    evidence: list[dict[str, Any]] = field(default_factory=list)
    model_id: str = ""
    prompt_version: str = ""
    rationale: str = ""
    source_tool: str = ""
    detector_id: str = "llm_investigate"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _check_evidence(prop: CandidateProposal) -> list[str]:
    if prop.kind in {"no_finding", "extractor_change", "pattern"}:
        return []
    if not prop.evidence and not prop.payload.get("documentation"):
        return ["missing_provenance"]
    return []


def _check_scope(prop: CandidateProposal) -> list[str]:
    reasons: list[str] = []
    if prop.kind == "operation":
        method = str(prop.payload.get("http_method") or prop.payload.get("method") or "").upper()
        path = str(prop.payload.get("http_path") or prop.payload.get("path") or "")
        if method and method not in HTTP_METHODS:
            reasons.append(f"bad_method:{method}")
        if not path.startswith("/"):
            reasons.append("path_not_absolute")
    return reasons


def _check_boundary(prop: CandidateProposal) -> list[str]:
    """Implementation facts must not become governed capability relationships."""
    if prop.kind not in {"relationship", "capability_link"}:
        return []
    kind = str(prop.payload.get("kind") or prop.kind)
    if kind not in GOVERNED_KINDS and prop.kind != "capability_link":
        return []
    for ev in prop.evidence:
        did = str(ev.get("detector_id") or "")
        if did in IMPLEMENTATION_DETECTORS or did.startswith("graphify"):
            return ["boundary_implementation_to_capability"]
    # Promoting a call-graph hint without non-impl evidence
    if prop.source_tool in {"read_file_window", "graphify"} and prop.kind == "capability_link":
        return ["boundary_implementation_to_capability"]
    return []


def _check_conflict_with_established(
    prop: CandidateProposal,
    established_ops: set[str] | None,
) -> list[str]:
    """Contradiction becomes conflict candidate — never silent overwrite."""
    if prop.kind != "operation" or not established_ops:
        return []
    method = str(prop.payload.get("http_method") or prop.payload.get("method") or "").upper()
    path = str(prop.payload.get("http_path") or prop.payload.get("path") or "")
    key = f"{method}:{path}"
    # Same identity with different action would be a conflict resolution path
    if key in established_ops and prop.kind == "operation":
        # Allow enriching existing; reject inventing a duplicate identity as new
        if prop.payload.get("as_new") is True:
            return ["conflicts_established_operation"]
    return []


def _try_schema(prop: CandidateProposal) -> list[str]:
    try:
        if prop.kind == "operation":
            method = str(prop.payload.get("http_method") or prop.payload.get("method") or "GET")
            path = str(prop.payload.get("http_path") or prop.payload.get("path") or "")
            ApiOperationFact(
                operation_key=str(prop.payload.get("operation_key") or f"{method}:{path}"),
                http_method=method.upper(),
                http_path=path,
                controller=str(prop.payload.get("controller") or "Unknown"),
                action=str(prop.payload.get("action") or "Unknown"),
                authz_policy=prop.payload.get("authz_policy"),
                authz_source=prop.payload.get("authz_source") or "unknown",  # type: ignore[arg-type]
                read_only=bool(prop.payload.get("read_only", method.upper() == "GET")),
                summary=prop.payload.get("summary"),
                evidence=[
                    Evidence.from_dict(e) if isinstance(e, dict) else e  # type: ignore[misc]
                    for e in prop.evidence
                    if isinstance(e, dict)
                ],
            )
        elif prop.kind == "relationship":
            evs = [
                Evidence.from_dict(e)
                for e in prop.evidence
                if isinstance(e, dict) and "repository_id" in e
            ]
            if not evs and prop.evidence:
                # Minimal evidence stub from free-form refs
                evs = [
                    Evidence(
                        repository_id=prop.repository_id,
                        commit_sha=str(prop.payload.get("commit_sha") or ""),
                        file_path=str(e.get("file_path") or "unknown"),
                        line_start=int(e.get("line_start") or 1),
                        line_end=int(e.get("line_end") or 1),
                        detector_id=prop.detector_id,
                        detector_version="1.0.0",
                        confidence=float(prop.payload.get("confidence") or 0.5),
                    )
                    for e in prop.evidence
                    if isinstance(e, dict)
                ]
            rel = CrossAppRelationship(
                relationship_id=str(prop.payload.get("relationship_id") or "pending"),
                kind=str(prop.payload.get("kind") or ""),
                from_application=str(prop.payload.get("from_application") or ""),
                to_application=str(prop.payload.get("to_application") or ""),
                confidence=float(prop.payload.get("confidence") or 0.5),
                evidence=evs,
                review_status="pending_review",
                detector_id=prop.detector_id,
                detector_version="1.0.0",
            )
            if not rel.kind or not rel.from_application:
                return ["schema_relationship_incomplete"]
        elif prop.kind == "pattern":
            if not prop.payload.get("yaml_fragment") and not prop.payload.get("pattern_file"):
                return ["schema_pattern_missing_yaml"]
        elif prop.kind == "no_finding":
            return []
    except Exception as exc:  # noqa: BLE001
        return [f"schema_error:{type(exc).__name__}"]
    return []


def validate_candidate(
    prop: CandidateProposal,
    *,
    established_op_keys: set[str] | None = None,
) -> GateVerdict:
    reasons: list[str] = []
    reasons.extend(_try_schema(prop))
    reasons.extend(_check_evidence(prop))
    reasons.extend(_check_scope(prop))
    reasons.extend(_check_boundary(prop))
    reasons.extend(_check_conflict_with_established(prop, established_op_keys))
    if reasons:
        return GateVerdict(accepted=False, reasons=reasons, tier="rejected")
    return GateVerdict(accepted=True, reasons=[], tier="candidate")
