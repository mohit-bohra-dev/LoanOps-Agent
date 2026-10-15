"""Backtest pattern proposals before git review (ADR-029)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from packages.eakg.gap_ledger import LedgerItem
from packages.eakg.models import RepoInterface
from packages.eakg.patterns import PatternSet, load_patterns


@dataclass
class BacktestReport:
    passed: bool
    motivating_resolved: int
    motivating_total: int
    established_changed: list[str] = field(default_factory=list)
    unrequested_matches: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sdk_match(package_id: str, patterns: PatternSet) -> str | None:
    for suf in patterns.sdk_client_suffixes:
        if package_id.endswith(suf):
            return "client"
    for suf in patterns.sdk_domain_suffixes:
        if package_id.endswith(suf):
            return "domain"
    return None


def _apply_sdk_patterns(
    ifaces: list[RepoInterface],
    patterns: PatternSet,
) -> set[str]:
    """Return package ids that would match SDK patterns."""
    hits: set[str] = set()
    for iface in ifaces:
        for pkg in iface.packages:
            pid = str(pkg.get("package_id") or "")
            if _sdk_match(pid, patterns):
                hits.add(pid)
    return hits


def _apply_owner_patterns(
    catalogs: set[str],
    patterns: PatternSet,
) -> dict[str, str]:
    out: dict[str, str] = {}
    for cat in catalogs:
        owner = patterns.datastore_owners.get(cat.lower()) or patterns.datastore_owners.get(cat)
        if owner:
            out[cat] = owner
    return out


def backtest_pattern_proposal(
    *,
    proposal_payload: dict[str, Any],
    motivating_items: list[LedgerItem],
    established_interfaces: list[RepoInterface],
    baseline_patterns: PatternSet | None = None,
    candidate_patterns: PatternSet | None = None,
) -> BacktestReport:
    """
    Fail if established facts would change.
    Report motivating recall and unrequested matches.
    """
    baseline = baseline_patterns or PatternSet()
    candidate = candidate_patterns
    if candidate is None:
        # Merge yaml_fragment into a synthetic PatternSet when possible
        fragment = str(proposal_payload.get("yaml_fragment") or "")
        pattern_file = str(proposal_payload.get("pattern_file") or "")
        candidate = _patterns_from_fragment(pattern_file, fragment, baseline)

    baseline_sdk = _apply_sdk_patterns(established_interfaces, baseline)
    candidate_sdk = _apply_sdk_patterns(established_interfaces, candidate)
    changed = sorted(baseline_sdk.symmetric_difference(candidate_sdk))
    # Losing a previously matched package is a regression
    regressions = sorted(baseline_sdk - candidate_sdk)

    catalogs: set[str] = set()
    for iface in established_interfaces:
        for key in iface.connection_keys:
            catalogs.add(key)
    base_owners = _apply_owner_patterns(catalogs, baseline)
    cand_owners = _apply_owner_patterns(catalogs, candidate)
    owner_changed = [
        f"{k}:{base_owners.get(k)}->{cand_owners.get(k)}"
        for k in set(base_owners) | set(cand_owners)
        if base_owners.get(k) != cand_owners.get(k)
    ]

    established_changed = [f"sdk:{x}" for x in regressions] + [
        f"owner:{x}" for x in owner_changed if base_owners
    ]

    # Motivating: openapi/cross_app/taac items whose keys appear in new matches
    new_only = candidate_sdk - baseline_sdk
    resolved = 0
    for item in motivating_items:
        ctx = item.context
        needle = str(ctx.get("key") or ctx.get("feature") or ctx.get("public_id") or "")
        if needle and any(needle in m or m in needle for m in new_only):
            resolved += 1
        elif item.shape_key and "sdk" in item.shape_key and new_only:
            resolved += 1

    unrequested = sorted(new_only)

    reasons: list[str] = []
    if established_changed:
        reasons.append("changes_established_facts")
        return BacktestReport(
            passed=False,
            motivating_resolved=resolved,
            motivating_total=len(motivating_items),
            established_changed=established_changed,
            unrequested_matches=unrequested,
            reasons=reasons,
        )

    return BacktestReport(
        passed=True,
        motivating_resolved=resolved,
        motivating_total=len(motivating_items),
        established_changed=[],
        unrequested_matches=unrequested,
        reasons=[],
    )


def _patterns_from_fragment(
    pattern_file: str,
    fragment: str,
    baseline: PatternSet,
) -> PatternSet:
    """Best-effort merge of a YAML fragment into a PatternSet copy."""
    import yaml  # type: ignore[import-untyped]

    raw: dict[str, Any] = {}
    try:
        loaded = yaml.safe_load(fragment) if fragment else {}
        if isinstance(loaded, dict):
            raw = loaded
    except Exception:  # noqa: BLE001
        return baseline

    client = list(baseline.sdk_client_suffixes)
    domain = list(baseline.sdk_domain_suffixes)
    owners = dict(baseline.datastore_owners)

    if "sdk_suffixes" in pattern_file or "client_suffixes" in raw or "domain_suffixes" in raw:
        if "client_suffixes" in raw:
            client = [str(x) for x in (raw["client_suffixes"] or [])]
        if "domain_suffixes" in raw:
            domain = [str(x) for x in (raw["domain_suffixes"] or [])]
    if "datastore" in pattern_file or "owners" in raw:
        own = raw.get("owners") if isinstance(raw.get("owners"), dict) else raw
        for k, v in (own or {}).items():
            if k in {"added_by", "approved_by", "approved_at", "motivating"}:
                continue
            owners[str(k)] = str(v)

    return PatternSet(
        sdk_client_suffixes=client,
        sdk_domain_suffixes=domain,
        datastore_owners=owners,
        proxy_base_classes=list(baseline.proxy_base_classes),
        service_url_key_suffixes=list(baseline.service_url_key_suffixes),
        topic_key_suffixes=list(baseline.topic_key_suffixes),
        router_names=list(baseline.router_names),
        decorator_names=list(baseline.decorator_names),
        version_blob=baseline.version_blob + "\n" + fragment,
    )


def backtest_from_dirs(
    *,
    patterns_dir: str,
    proposal_payload: dict[str, Any],
    motivating_items: list[LedgerItem],
    interfaces: list[RepoInterface],
) -> BacktestReport:
    baseline = load_patterns(patterns_dir)
    return backtest_pattern_proposal(
        proposal_payload=proposal_payload,
        motivating_items=motivating_items,
        established_interfaces=interfaces,
        baseline_patterns=baseline,
    )
