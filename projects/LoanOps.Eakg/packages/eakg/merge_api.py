"""Merge ApiOperationFact lists from multiple analyzers into one RepoInterface."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from packages.eakg.analyzers.types import AnalyzerResult
from packages.eakg.models import ApiOperationFact, Evidence, RepoInterface
from packages.eakg.route_identity import fact_rank, normalize_path, route_key


@dataclass
class ConflictRecord:
    """Two analyzers disagree on a non-identity field for the same route key."""

    route_key: str
    field: str
    preferred_value: Any
    other_value: Any
    preferred_detector: str
    other_detector: str
    preferred_evidence: list[dict[str, Any]] = field(default_factory=list)
    other_evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_key": self.route_key,
            "field": self.field,
            "preferred_value": self.preferred_value,
            "other_value": self.other_value,
            "preferred_detector": self.preferred_detector,
            "other_detector": self.other_detector,
            "preferred_evidence": list(self.preferred_evidence),
            "other_evidence": list(self.other_evidence),
        }


@dataclass
class MergeResult:
    iface: RepoInterface
    facts: list[ApiOperationFact]
    detector_versions: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    language_counts: dict[str, int] = field(default_factory=dict)
    extractors: list[str] = field(default_factory=list)
    conflicts: list[ConflictRecord] = field(default_factory=list)


def _evidence_sig(ev: Evidence) -> tuple[str, str, int, str]:
    return (ev.file_path, ev.detector_id, ev.line_start, ev.commit_sha)


def _merge_evidence(preferred: list[Evidence], other: list[Evidence]) -> list[Evidence]:
    seen = {_evidence_sig(e) for e in preferred}
    out = list(preferred)
    for ev in other:
        sig = _evidence_sig(ev)
        if sig not in seen:
            seen.add(sig)
            out.append(ev)
    return out


def _fact_to_op_dict(op: ApiOperationFact) -> dict[str, Any]:
    row: dict[str, Any] = {
        "key": op.operation_key,
        "method": op.http_method,
        "path": op.http_path,
        "controller": op.controller,
        "action": op.action,
        "authz_policy": op.authz_policy,
        "authz_source": op.authz_source,
        "read_only": op.read_only,
    }
    if op.summary:
        row["summary"] = op.summary
    return row


def empty_repo_interface(
    *,
    repository_id: str,
    application_id: str,
    commit_sha: str,
) -> RepoInterface:
    return RepoInterface(
        repository_id=repository_id,
        application_id=application_id,
        commit_sha=commit_sha,
    )


def merge_operation_facts(
    facts: list[ApiOperationFact],
    *,
    base: RepoInterface | None = None,
    repository_id: str = "",
    application_id: str = "",
    commit_sha: str = "",
) -> MergeResult:
    """Dedupe by canonical route_key; preferred metadata by fact_rank; merge evidence."""
    groups: dict[str, list[ApiOperationFact]] = {}
    for fact in facts:
        if not isinstance(fact, ApiOperationFact):
            continue
        method = (fact.http_method or "GET").upper()
        path = normalize_path(fact.http_path)
        key = route_key(method, path)
        # Keep normalized path on the fact used for merge
        normalized = replace(
            fact,
            http_method=method,
            http_path=path,
            operation_key=fact.operation_key or f"{key}:{fact.controller}.{fact.action}",
        )
        groups.setdefault(key, []).append(normalized)

    merged: list[ApiOperationFact] = []
    conflicts: list[ConflictRecord] = []
    compare_fields = ("authz_policy", "action", "controller", "read_only", "summary")
    for key in sorted(groups):
        candidates = groups[key]
        candidates.sort(
            key=lambda f: (
                fact_rank(
                    f.evidence[0].detector_id if f.evidence else "",
                    f.controller,
                ),
                f.controller,
                f.action,
            )
        )
        preferred = candidates[0]
        pref_det = preferred.evidence[0].detector_id if preferred.evidence else ""
        evidence = list(preferred.evidence)
        for other in candidates[1:]:
            evidence = _merge_evidence(evidence, other.evidence)
            other_det = other.evidence[0].detector_id if other.evidence else ""
            for fname in compare_fields:
                pv = getattr(preferred, fname)
                ov = getattr(other, fname)
                if pv != ov and (pv is not None or ov is not None):
                    conflicts.append(
                        ConflictRecord(
                            route_key=key,
                            field=fname,
                            preferred_value=pv,
                            other_value=ov,
                            preferred_detector=pref_det,
                            other_detector=other_det,
                            preferred_evidence=[e.to_dict() for e in preferred.evidence[:3]],
                            other_evidence=[
                                f"{e.file_path}:{e.line_start}" for e in other.evidence[:3]
                            ],
                        )
                    )
        merged.append(replace(preferred, evidence=evidence))

    versions: dict[str, str] = {}
    lang_counts: dict[str, int] = {}
    for fact in merged:
        for ev in fact.evidence:
            versions[ev.detector_id] = ev.detector_version
        did = fact.evidence[0].detector_id if fact.evidence else ""
        if did.startswith("dotnet"):
            lang = "csharp"
        elif "python" in did:
            lang = "python"
        elif "node" in did:
            lang = "javascript"
        else:
            lang = "other"
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

    if base is not None:
        iface = RepoInterface(
            repository_id=base.repository_id,
            application_id=base.application_id,
            commit_sha=base.commit_sha,
            packages=list(base.packages),
            operations=[_fact_to_op_dict(o) for o in merged],
            service_url_keys=list(base.service_url_keys),
            topics=list(base.topics),
            connection_keys=list(base.connection_keys),
            proxies=list(base.proxies),
            route_compositions=list(base.route_compositions),
            auth_packages=list(base.auth_packages),
        )
    else:
        iface = empty_repo_interface(
            repository_id=repository_id,
            application_id=application_id,
            commit_sha=commit_sha,
        )
        iface.operations = [_fact_to_op_dict(o) for o in merged]

    return MergeResult(
        iface=iface,
        conflicts=conflicts,
        facts=merged,
        detector_versions=versions,
        language_counts=lang_counts,
    )


def merge_api_results(
    results: list[AnalyzerResult],
    *,
    repository_id: str,
    application_id: str,
    commit_sha: str,
) -> MergeResult:
    """Compose analyzer results into one interface + fact list."""
    warnings: list[str] = []
    extractors: list[str] = []
    all_facts: list[ApiOperationFact] = []
    base: RepoInterface | None = None

    for result in results:
        if result.error:
            warnings.append(str(result.error))
        ext = result.extra.get("extractor")
        if isinstance(ext, str) and ext:
            extractors.append(ext)
        elif isinstance(ext, list):
            extractors.extend(str(x) for x in ext)
        warn_list = result.extra.get("warnings")
        if isinstance(warn_list, list):
            warnings.extend(str(w) for w in warn_list)

        facts_obj = result.extra.get("operation_facts")
        if isinstance(facts_obj, list):
            all_facts.extend(o for o in facts_obj if isinstance(o, ApiOperationFact))
        else:
            details = result.extra.get("details")
            if isinstance(details, dict):
                ops = details.get("operations")
                if isinstance(ops, list):
                    all_facts.extend(o for o in ops if isinstance(o, ApiOperationFact))

        iface_obj = result.extra.get("repo_interface")
        if isinstance(iface_obj, RepoInterface) and base is None:
            base = iface_obj

    if base is None:
        base = empty_repo_interface(
            repository_id=repository_id,
            application_id=application_id,
            commit_sha=commit_sha,
        )

    merged = merge_operation_facts(
        all_facts,
        base=base,
        repository_id=repository_id,
        application_id=application_id,
        commit_sha=commit_sha,
    )
    merged.warnings = warnings
    merged.extractors = extractors
    return merged


def rebuild_interface_from_facts(
    iface: RepoInterface,
    facts: list[ApiOperationFact],
) -> RepoInterface:
    """Replace operations on an existing interface (used after OpenAPI enrich)."""
    return RepoInterface(
        repository_id=iface.repository_id,
        application_id=iface.application_id,
        commit_sha=iface.commit_sha,
        packages=list(iface.packages),
        operations=[_fact_to_op_dict(o) for o in facts],
        service_url_keys=list(iface.service_url_keys),
        topics=list(iface.topics),
        connection_keys=list(iface.connection_keys),
        proxies=list(iface.proxies),
        route_compositions=list(iface.route_compositions),
        auth_packages=list(iface.auth_packages),
    )
