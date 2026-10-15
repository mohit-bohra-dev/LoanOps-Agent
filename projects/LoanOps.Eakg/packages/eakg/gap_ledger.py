"""Deterministic gap / ambiguity ledger (ADR-029). Sole input to the investigator."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

from packages.eakg.coverage import CoverageManifest
from packages.eakg.merge_api import ConflictRecord
from packages.eakg.models import RepoInterface


@dataclass
class LedgerItem:
    item_id: str
    shape_key: str
    source: str  # coverage | openapi | cross_app | process | taac | code | conflict
    kind: str
    repository_id: str
    context: dict[str, Any] = field(default_factory=dict)
    status: str = "open"  # open | proposed | closed_no_finding | absorbed_by_pattern

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> LedgerItem:
        return cls(
            item_id=str(raw["item_id"]),
            shape_key=str(raw["shape_key"]),
            source=str(raw["source"]),
            kind=str(raw["kind"]),
            repository_id=str(raw.get("repository_id") or ""),
            context=dict(raw.get("context") or {}),
            status=str(raw.get("status") or "open"),
        )


def _id(*parts: str) -> str:
    blob = "|".join(parts).encode("utf-8")
    return "gap_" + hashlib.sha256(blob).hexdigest()[:16]


def shape_key(source: str, kind: str, feature: str) -> str:
    feat = feature.strip().lower().replace(" ", "_")[:80]
    return f"{source}:{kind}:{feat}"


def from_coverage(manifest: CoverageManifest) -> list[LedgerItem]:
    out: list[LedgerItem] = []
    rid = manifest.repository_id
    for reason in manifest.incomplete_reasons:
        if reason.startswith("analyzer_error:"):
            rest = reason.split(":", 2)
            aid = rest[1] if len(rest) > 1 else "unknown"
            sk = shape_key("coverage", "analyzer_error", aid)
            out.append(
                LedgerItem(
                    item_id=_id(rid, reason),
                    shape_key=sk,
                    source="coverage",
                    kind="analyzer_error",
                    repository_id=rid,
                    context={"reason": reason, "analyzer_id": aid},
                )
            )
        elif reason.startswith("zero_operations:"):
            aid = reason.split(":", 1)[-1]
            sk = shape_key("code", "no_ops", aid)
            out.append(
                LedgerItem(
                    item_id=_id(rid, reason),
                    shape_key=sk,
                    source="code",
                    kind="no_ops",
                    repository_id=rid,
                    context={"reason": reason, "analyzer_id": aid},
                )
            )
        elif reason.startswith("unsupported_language:"):
            lang = reason.split(":", 1)[-1]
            sk = shape_key("code", "unsupported_language", lang)
            out.append(
                LedgerItem(
                    item_id=_id(rid, reason),
                    shape_key=sk,
                    source="code",
                    kind="unsupported_language",
                    repository_id=rid,
                    context={"language": lang},
                )
            )
        elif reason.startswith("required_analyzer_not_run:"):
            aid = reason.split(":", 1)[-1]
            sk = shape_key("coverage", "not_run", aid)
            out.append(
                LedgerItem(
                    item_id=_id(rid, reason),
                    shape_key=sk,
                    source="coverage",
                    kind="not_run",
                    repository_id=rid,
                    context={"analyzer_id": aid},
                )
            )
        else:
            sk = shape_key("coverage", "incomplete", reason[:40])
            out.append(
                LedgerItem(
                    item_id=_id(rid, reason),
                    shape_key=sk,
                    source="coverage",
                    kind="incomplete",
                    repository_id=rid,
                    context={"reason": reason},
                )
            )
    return out


def from_conflicts(
    conflicts: list[ConflictRecord],
    *,
    repository_id: str,
) -> list[LedgerItem]:
    out: list[LedgerItem] = []
    for c in conflicts:
        sk = shape_key("conflict", c.field, c.route_key)
        out.append(
            LedgerItem(
                item_id=_id(repository_id, c.route_key, c.field, str(c.other_value)),
                shape_key=sk,
                source="conflict",
                kind="field_mismatch",
                repository_id=repository_id,
                context=c.to_dict(),
            )
        )
    return out


def from_openapi_join_report(
    report: dict[str, Any],
    *,
    repository_id: str = "",
) -> list[LedgerItem]:
    """ApiIndex mismatch report → ledger items."""
    out: list[LedgerItem] = []
    for join_kind in ("openapi_only", "eakg_only", "ambiguous"):
        rows = report.get(join_kind) or []
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict):
                pid = str(row.get("public_id") or row.get("eakg_key") or row.get("path") or "")
                app = str(row.get("app") or repository_id)
                ctx: dict[str, Any] = {**row, "join": join_kind}
            else:
                pid = str(row)
                app = pid.split(":", 1)[0] if ":" in pid else repository_id
                ctx = {"public_id": pid, "join": join_kind}
            rid = repository_id or app
            # Feature is join kind (not per-op id) so recurrence can trigger patterns
            sk = shape_key("openapi", join_kind, "join_gap")
            out.append(
                LedgerItem(
                    item_id=_id("openapi", join_kind, pid or json.dumps(row, sort_keys=True)[:40]),
                    shape_key=sk,
                    source="openapi",
                    kind=join_kind,
                    repository_id=rid,
                    context=ctx,
                )
            )
    return out


def from_detector_near_misses(
    near_misses: list[dict[str, Any]],
    *,
    repository_id: str,
) -> list[LedgerItem]:
    out: list[LedgerItem] = []
    for row in near_misses:
        kind = str(row.get("kind") or "near_miss")
        feature = str(row.get("feature") or row.get("to_application") or "unknown")
        sk = shape_key("cross_app", kind, feature)
        out.append(
            LedgerItem(
                item_id=_id(repository_id, kind, feature, json.dumps(row, sort_keys=True)[:80]),
                shape_key=sk,
                source="cross_app",
                kind=kind,
                repository_id=repository_id,
                context=dict(row),
            )
        )
    return out


def from_process_draft(draft: Any, *, repository_id: str = "process") -> list[LedgerItem]:
    """ProcessDraft with partial/stub or NeedsReview → ledger."""
    out: list[LedgerItem] = []
    status = str(getattr(draft, "extraction_status", "") or "")
    page_id = str(getattr(draft, "page_id", "") or getattr(draft, "procedure_id", "") or "page")
    if status in {"partial", "stub"}:
        sk = shape_key("process", status, page_id)
        out.append(
            LedgerItem(
                item_id=_id("process", status, page_id),
                shape_key=sk,
                source="process",
                kind=status,
                repository_id=repository_id,
                context={"page_id": page_id, "extraction_status": status},
            )
        )
    needs = getattr(draft, "needs_review", None) or []
    for nr in needs:
        if isinstance(nr, dict):
            reason = str(nr.get("reason") or "")
        else:
            reason = str(getattr(nr, "reason", "") or "")
        if not reason:
            continue
        sk = shape_key("process", "needs_review", reason[:40])
        out.append(
            LedgerItem(
                item_id=_id("process", page_id, reason),
                shape_key=sk,
                source="process",
                kind="needs_review",
                repository_id=repository_id,
                context={"page_id": page_id, "reason": reason},
            )
        )
    return out


def from_unmapped_taac(
    unmapped_keys: list[str],
    *,
    kind: str = "unmapped_service_url",
) -> list[LedgerItem]:
    out: list[LedgerItem] = []
    for key in unmapped_keys:
        sk = shape_key("taac", kind, key)
        out.append(
            LedgerItem(
                item_id=_id("taac", kind, key),
                shape_key=sk,
                source="taac",
                kind=kind,
                repository_id="enterprise",
                context={"key": key},
            )
        )
    return out


def unmapped_service_urls(
    ifaces: list[RepoInterface],
    url_key_to_app: dict[str, str],
) -> list[str]:
    """ServiceUrl keys present in interfaces but missing from TAAC map."""
    missing: list[str] = []
    for iface in ifaces:
        for key in iface.service_url_keys:
            if key not in url_key_to_app:
                missing.append(key)
    return sorted(set(missing))


def count_by_shape(items: list[LedgerItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for it in items:
        if it.status != "open":
            continue
        counts[it.shape_key] = counts.get(it.shape_key, 0) + 1
    return counts


def shapes_eligible_for_pattern(
    items: list[LedgerItem],
    *,
    min_count: int = 3,
) -> set[str]:
    return {sk for sk, n in count_by_shape(items).items() if n >= min_count}


def build_ledger(
    *,
    coverage: CoverageManifest | None = None,
    conflicts: list[ConflictRecord] | None = None,
    openapi_report: dict[str, Any] | None = None,
    near_misses: list[dict[str, Any]] | None = None,
    process_drafts: list[Any] | None = None,
    unmapped_taac: list[str] | None = None,
    repository_id: str = "",
) -> list[LedgerItem]:
    items: list[LedgerItem] = []
    if coverage is not None:
        items.extend(from_coverage(coverage))
    if conflicts:
        rid = repository_id or (coverage.repository_id if coverage else "")
        items.extend(from_conflicts(conflicts, repository_id=rid))
    if openapi_report:
        items.extend(from_openapi_join_report(openapi_report, repository_id=repository_id))
    if near_misses:
        items.extend(
            from_detector_near_misses(near_misses, repository_id=repository_id or "cross_app")
        )
    if process_drafts:
        for d in process_drafts:
            items.extend(from_process_draft(d))
    if unmapped_taac:
        items.extend(from_unmapped_taac(unmapped_taac))
    # Dedupe by item_id
    seen: set[str] = set()
    unique: list[LedgerItem] = []
    for it in items:
        if it.item_id in seen:
            continue
        seen.add(it.item_id)
        unique.append(it)
    return unique
