"""Shared EAKG models (extractors, detectors, registry)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

IndexStatus = Literal[
    "registered",
    "cloning",
    "extracting",
    "enriching",
    "pending_review",
    "indexed",
    "failed",
]
AccessStatus = Literal["ok", "no_access", "auth_required"]
AuthzSource = Literal["attribute", "class-level", "convention", "unknown"]


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass
class Evidence:
    """Provenance for one structural or proposed claim."""

    repository_id: str
    commit_sha: str
    file_path: str
    line_start: int
    line_end: int
    detector_id: str
    detector_version: str
    confidence: float
    extracted_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Evidence:
        return cls(
            repository_id=str(raw["repository_id"]),
            commit_sha=str(raw["commit_sha"]),
            file_path=str(raw["file_path"]),
            line_start=int(raw["line_start"]),
            line_end=int(raw["line_end"]),
            detector_id=str(raw["detector_id"]),
            detector_version=str(raw["detector_version"]),
            confidence=float(raw["confidence"]),
            extracted_at=str(raw.get("extracted_at") or utc_now_iso()),
        )


@dataclass
class ApiOperationFact:
    operation_key: str
    http_method: str
    http_path: str
    controller: str
    action: str
    authz_policy: str | None
    authz_source: AuthzSource
    read_only: bool
    summary: str | None = None
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class PackageRefFact:
    package_id: str
    version: str | None
    project_path: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class ServiceUrlFact:
    key: str
    usage_kind: str  # options_value | lambda_member | string_literal | config
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class ProxyFact:
    class_name: str
    base_class: str
    url_key: str | None
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class TopicFact:
    topic_key: str
    topic_value: str
    role: Literal["publish", "subscribe", "declare"]
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class ConnectionFact:
    connection_key: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class RouteCompositionFact:
    caller_symbol: str
    composed_path: str
    http_method: str | None
    url_key: str | None
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class RepoInterface:
    """Compact join surface for cross-app detectors (content-hashed)."""

    repository_id: str
    application_id: str
    commit_sha: str
    packages: list[dict[str, Any]] = field(default_factory=list)
    operations: list[dict[str, Any]] = field(default_factory=list)
    service_url_keys: list[str] = field(default_factory=list)
    topics: list[dict[str, Any]] = field(default_factory=list)
    connection_keys: list[str] = field(default_factory=list)
    proxies: list[dict[str, Any]] = field(default_factory=list)
    route_compositions: list[dict[str, Any]] = field(default_factory=list)
    auth_packages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> RepoInterface:
        return cls(
            repository_id=str(raw["repository_id"]),
            application_id=str(raw.get("application_id") or ""),
            commit_sha=str(raw.get("commit_sha") or ""),
            packages=list(raw.get("packages") or []),
            operations=list(raw.get("operations") or []),
            service_url_keys=list(raw.get("service_url_keys") or []),
            topics=list(raw.get("topics") or []),
            connection_keys=list(raw.get("connection_keys") or []),
            proxies=list(raw.get("proxies") or []),
            route_compositions=list(raw.get("route_compositions") or []),
            auth_packages=list(raw.get("auth_packages") or []),
        )


@dataclass
class CrossAppRelationship:
    """First-class edge; invalid without evidence."""

    relationship_id: str
    kind: str
    from_application: str
    to_application: str
    confidence: float
    evidence: list[Evidence]
    to_operation: str | None = None
    to_package: str | None = None
    to_topic: str | None = None
    to_datastore: str | None = None
    to_auth: str | None = None
    review_status: str = "discovered"
    detector_id: str = ""
    detector_version: str = ""

    def validate(self) -> bool:
        return bool(self.evidence) and bool(self.kind) and bool(self.relationship_id)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["evidence"] = [e.to_dict() for e in self.evidence]
        return d


@dataclass
class Proposal:
    proposal_id: str
    kind: Literal["capability_label", "capability_group", "overlap_wording", "rationale"]
    repository_id: str
    content_hash: str
    payload: dict[str, Any]
    confidence: float
    evidence_refs: list[str] = field(default_factory=list)
    status: str = "pending_review"
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
