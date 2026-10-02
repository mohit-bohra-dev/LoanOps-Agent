"""Cross-application relationship detectors (evidence required)."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass

from packages.capability_kg.ontology import (
    KIND_AUTHENTICATES_VIA,
    KIND_CALLS_APPLICATION,
    KIND_CALLS_OPERATION,
    KIND_CONSUMES_SDK,
    KIND_OVERLAPS_CAPABILITY,
    KIND_PUBLISHES_EVENT,
    KIND_READS_DATASTORE,
    KIND_SHARES_DTO,
    RELATIONSHIP_KINDS,
)
from packages.eakg.models import CrossAppRelationship, Evidence, RepoInterface, utc_now_iso
from packages.eakg.taac import normalize_topic, url_key_to_app_id


def _rid(*parts: str) -> str:
    h = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"rel_{h}"


def _ev_from_iface(
    iface: RepoInterface,
    *,
    file_path: str,
    line: int,
    detector_id: str,
    version: str,
    confidence: float,
) -> Evidence:
    return Evidence(
        repository_id=iface.repository_id,
        commit_sha=iface.commit_sha,
        file_path=file_path,
        line_start=line,
        line_end=line,
        detector_id=detector_id,
        detector_version=version,
        confidence=confidence,
        extracted_at=utc_now_iso(),
    )


@dataclass
class EnterpriseIndex:
    """Join helpers from TAAC + all repo interfaces."""

    url_key_to_app: dict[str, str]
    connection_key_to_catalog: dict[str, str]
    catalog_owner_app: dict[str, str]  # LoanServicing → loanservices
    interfaces: dict[str, RepoInterface]

    def app_for_package(self, package_id: str) -> str | None:
        # PNMAC.LoanServices.Client → loanservices
        m = re.match(r"PNMAC\.([A-Za-z0-9]+)\.(Client|Domain)\b", package_id)
        if not m:
            return None
        return m.group(1).lower()


DetectorFn = Callable[
    [RepoInterface, EnterpriseIndex],
    list[CrossAppRelationship],
]


def detect_nuget_sdk(iface: RepoInterface, index: EnterpriseIndex) -> list[CrossAppRelationship]:
    out: list[CrossAppRelationship] = []
    for pkg in iface.packages:
        pid = str(pkg.get("package_id") or "")
        target = index.app_for_package(pid)
        if not target or target == iface.application_id:
            continue
        kind = KIND_CONSUMES_SDK if pid.endswith(".Client") else KIND_SHARES_DTO
        if kind == KIND_SHARES_DTO and not pid.endswith(".Domain"):
            continue
        ev = _ev_from_iface(
            iface,
            file_path=str(pkg.get("project") or "unknown.csproj"),
            line=1,
            detector_id="nuget_sdk",
            version="1.0.0",
            confidence=1.0,
        )
        out.append(
            CrossAppRelationship(
                relationship_id=_rid(iface.application_id, kind, target, pid),
                kind=kind,
                from_application=iface.application_id,
                to_application=target,
                to_package=pid,
                confidence=1.0,
                evidence=[ev],
                detector_id="nuget_sdk",
                detector_version="1.0.0",
                review_status="approved" if True else "discovered",
            )
        )
    return out


def detect_service_url(iface: RepoInterface, index: EnterpriseIndex) -> list[CrossAppRelationship]:
    out: list[CrossAppRelationship] = []
    for key in iface.service_url_keys:
        target = index.url_key_to_app.get(key) or url_key_to_app_id(key)
        if target == iface.application_id:
            continue
        # skip self LoanServicesUrl inside loanservices
        if key.lower().startswith(iface.application_id.replace("_", "").lower()):
            # still allow if different app mapping
            pass
        if target == iface.application_id:
            continue
        ev = _ev_from_iface(
            iface,
            file_path="config/ServiceUrls",
            line=1,
            detector_id="service_url",
            version="1.0.0",
            confidence=0.9,
        )
        out.append(
            CrossAppRelationship(
                relationship_id=_rid(iface.application_id, KIND_CALLS_APPLICATION, target, key),
                kind=KIND_CALLS_APPLICATION,
                from_application=iface.application_id,
                to_application=target,
                confidence=0.9,
                evidence=[ev],
                detector_id="service_url",
                detector_version="1.0.0",
                review_status="discovered",
            )
        )
    return out


def detect_proxy_class(iface: RepoInterface, index: EnterpriseIndex) -> list[CrossAppRelationship]:
    out: list[CrossAppRelationship] = []
    for proxy in iface.proxies:
        url_key = proxy.get("url_key")
        if not url_key:
            continue
        target = index.url_key_to_app.get(str(url_key)) or url_key_to_app_id(str(url_key))
        if target == iface.application_id:
            continue
        ev = _ev_from_iface(
            iface,
            file_path=f"proxy/{proxy.get('class')}",
            line=1,
            detector_id="proxy_class",
            version="1.0.0",
            confidence=0.95,
        )
        out.append(
            CrossAppRelationship(
                relationship_id=_rid(
                    iface.application_id, KIND_CALLS_APPLICATION, target, str(proxy.get("class"))
                ),
                kind=KIND_CALLS_APPLICATION,
                from_application=iface.application_id,
                to_application=target,
                confidence=0.95,
                evidence=[ev],
                detector_id="proxy_class",
                detector_version="1.0.0",
                review_status="discovered",
            )
        )
    return out


def _norm_path(path: str) -> str:
    p = path.split("?")[0]
    p = re.sub(r"\{[^}]+\}", "{id}", p)
    p = re.sub(r"/(\d+)", "/{id}", p)
    return p.lower().rstrip("/")


def detect_route_composition(
    iface: RepoInterface, index: EnterpriseIndex
) -> list[CrossAppRelationship]:
    out: list[CrossAppRelationship] = []
    # Build target operation index from other apps
    op_index: dict[str, tuple[str, str]] = {}
    for other in index.interfaces.values():
        if other.repository_id == iface.repository_id:
            continue
        for op in other.operations:
            path = _norm_path(str(op.get("path") or ""))
            method = str(op.get("method") or "GET").upper()
            op_index[f"{method}:{path}"] = (other.application_id, str(op.get("key") or ""))

    for route in iface.route_compositions:
        composed = _norm_path(str(route.get("path") or ""))
        method = str(route.get("method") or "GET").upper()
        key = f"{method}:{composed}"
        # also try stripping /api prefix variants
        candidates = [key]
        if composed.startswith("/api/"):
            candidates.append(f"{method}:{composed}")
        hit = None
        for c in candidates:
            if c in op_index:
                hit = op_index[c]
                break
            # fuzzy: match suffix
            for k, v in op_index.items():
                if k.startswith(f"{method}:") and (
                    composed.endswith(k.split(":", 1)[1])
                    or k.split(":", 1)[1].endswith(composed.replace("/api", "", 1))
                ):
                    hit = v
                    break
            if hit:
                break
        if not hit:
            continue
        target_app, op_key = hit
        conf = 0.75
        url_key = route.get("url_key")
        if url_key:
            mapped = index.url_key_to_app.get(str(url_key)) or url_key_to_app_id(str(url_key))
            if mapped == target_app:
                conf = 0.85
        ev = _ev_from_iface(
            iface,
            file_path=f"route/{route.get('caller')}",
            line=1,
            detector_id="route_composition",
            version="1.0.0",
            confidence=conf,
        )
        out.append(
            CrossAppRelationship(
                relationship_id=_rid(
                    iface.application_id, KIND_CALLS_OPERATION, target_app, op_key, composed
                ),
                kind=KIND_CALLS_OPERATION,
                from_application=iface.application_id,
                to_application=target_app,
                to_operation=op_key,
                confidence=conf,
                evidence=[ev],
                detector_id="route_composition",
                detector_version="1.0.0",
                review_status="pending_review",
            )
        )
    return out


def detect_event_topic(iface: RepoInterface, index: EnterpriseIndex) -> list[CrossAppRelationship]:
    out: list[CrossAppRelationship] = []
    my_topics = {
        normalize_topic(str(t.get("value") or "")): t for t in iface.topics if t.get("value")
    }
    for other in index.interfaces.values():
        if other.repository_id == iface.repository_id:
            continue
        for t in other.topics:
            name = normalize_topic(str(t.get("value") or ""))
            if not name or name not in my_topics:
                continue
            ev = _ev_from_iface(
                iface,
                file_path="appsettings.json",
                line=1,
                detector_id="event_topic",
                version="1.0.0",
                confidence=0.95,
            )
            out.append(
                CrossAppRelationship(
                    relationship_id=_rid(
                        iface.application_id, KIND_PUBLISHES_EVENT, other.application_id, name
                    ),
                    kind=KIND_PUBLISHES_EVENT,
                    from_application=iface.application_id,
                    to_application=other.application_id,
                    to_topic=name,
                    confidence=0.95,
                    evidence=[ev],
                    detector_id="event_topic",
                    detector_version="1.0.0",
                    review_status="discovered",
                )
            )
    return out


def detect_data_store(iface: RepoInterface, index: EnterpriseIndex) -> list[CrossAppRelationship]:
    out: list[CrossAppRelationship] = []
    for key in iface.connection_keys:
        catalog = index.connection_key_to_catalog.get(key)
        if not catalog:
            # heuristic: LoanServicesContext → LoanServicing
            if "LoanService" in key:
                catalog = "LoanServicing"
            else:
                continue
        owner = index.catalog_owner_app.get(catalog.lower())
        if not owner:
            # LoanServicing owned by loanservices
            if "loanservic" in catalog.lower():
                owner = "loanservices"
            elif "fee" in catalog.lower():
                owner = "fees"
            elif "escrow" in catalog.lower():
                owner = "escrow"
            else:
                continue
        if owner == iface.application_id:
            continue
        ev = _ev_from_iface(
            iface,
            file_path="appsettings.json",
            line=1,
            detector_id="data_store",
            version="1.0.0",
            confidence=0.9,
        )
        out.append(
            CrossAppRelationship(
                relationship_id=_rid(
                    iface.application_id, KIND_READS_DATASTORE, owner, catalog, key
                ),
                kind=KIND_READS_DATASTORE,
                from_application=iface.application_id,
                to_application=owner,
                to_datastore=catalog,
                confidence=0.9,
                evidence=[ev],
                detector_id="data_store",
                detector_version="1.0.0",
                review_status="discovered",
            )
        )
    return out


def detect_auth_dependency(
    iface: RepoInterface, index: EnterpriseIndex
) -> list[CrossAppRelationship]:
    out: list[CrossAppRelationship] = []
    if not iface.auth_packages:
        return out
    ev = _ev_from_iface(
        iface,
        file_path="*.csproj",
        line=1,
        detector_id="auth_dependency",
        version="1.0.0",
        confidence=1.0,
    )
    out.append(
        CrossAppRelationship(
            relationship_id=_rid(iface.application_id, KIND_AUTHENTICATES_VIA, "auth0"),
            kind=KIND_AUTHENTICATES_VIA,
            from_application=iface.application_id,
            to_application="appservices",
            to_auth="Auth0",
            confidence=1.0,
            evidence=[ev],
            detector_id="auth_dependency",
            detector_version="1.0.0",
            review_status="approved",
        )
    )
    return out


def detect_capability_overlap(
    iface: RepoInterface, index: EnterpriseIndex
) -> list[CrossAppRelationship]:
    """Embedding-free token overlap heuristic; always pending_review."""
    out: list[CrossAppRelationship] = []
    my_actions = {str(o.get("action") or "").lower() for o in iface.operations}
    for other in index.interfaces.values():
        if other.repository_id == iface.repository_id:
            continue
        other_actions = {str(o.get("action") or "").lower() for o in other.operations}
        shared = my_actions & other_actions
        shared = {s for s in shared if s and len(s) > 4}
        if len(shared) < 2:
            continue
        ev = _ev_from_iface(
            iface,
            file_path="operations",
            line=1,
            detector_id="capability_overlap",
            version="1.0.0",
            confidence=0.5,
        )
        out.append(
            CrossAppRelationship(
                relationship_id=_rid(
                    iface.application_id,
                    KIND_OVERLAPS_CAPABILITY,
                    other.application_id,
                    ",".join(sorted(shared)[:3]),
                ),
                kind=KIND_OVERLAPS_CAPABILITY,
                from_application=iface.application_id,
                to_application=other.application_id,
                confidence=0.5,
                evidence=[ev],
                detector_id="capability_overlap",
                detector_version="1.0.0",
                review_status="pending_review",
            )
        )
    return out


ALL_DETECTORS: list[tuple[str, DetectorFn]] = [
    ("nuget_sdk", detect_nuget_sdk),
    ("service_url", detect_service_url),
    ("proxy_class", detect_proxy_class),
    ("route_composition", detect_route_composition),
    ("event_topic", detect_event_topic),
    ("data_store", detect_data_store),
    ("auth_dependency", detect_auth_dependency),
    ("capability_overlap", detect_capability_overlap),
]


def run_detectors(
    iface: RepoInterface,
    index: EnterpriseIndex,
    *,
    only: set[str] | None = None,
) -> tuple[list[CrossAppRelationship], int]:
    """Return valid relationships and count of dropped (no evidence) edges."""
    kept: list[CrossAppRelationship] = []
    dropped = 0
    for name, fn in ALL_DETECTORS:
        if only is not None and name not in only:
            continue
        for rel in fn(iface, index):
            if rel.kind not in RELATIONSHIP_KINDS:
                dropped += 1
                continue
            if not rel.validate():
                dropped += 1
                continue
            kept.append(rel)
    return kept, dropped
