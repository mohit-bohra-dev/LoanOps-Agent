"""Coverage manifest — required analyzers; not delegable to the LLM (ADR-029)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from packages.eakg.analyzers.protocol import Analyzer
from packages.eakg.analyzers.types import AnalyzerResult, Inventory


@dataclass
class AnalyzerRunRecord:
    analyzer_id: str
    version: str
    produces_api_surface: bool
    status: str  # ran | errored | skipped
    error: str | None = None
    operation_count: int = 0


@dataclass
class CoverageManifest:
    """Persisted required-set + completion. Agent may read, never rewrite."""

    repository_id: str
    required_analyzers: list[str]
    ran: list[AnalyzerRunRecord]
    unsupported_languages: list[str]
    inventory_languages: list[str]
    inventory_projects: list[str]
    patterns_hash: str = ""
    status: str = "complete"  # complete | incomplete
    incomplete_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["ran"] = [asdict(r) for r in self.ran]
        return d

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CoverageManifest:
        ran = [
            AnalyzerRunRecord(
                analyzer_id=str(r.get("analyzer_id") or ""),
                version=str(r.get("version") or ""),
                produces_api_surface=bool(r.get("produces_api_surface")),
                status=str(r.get("status") or "skipped"),
                error=r.get("error") if isinstance(r.get("error"), str) else None,
                operation_count=int(r.get("operation_count") or 0),
            )
            for r in (raw.get("ran") or [])
            if isinstance(r, dict)
        ]
        return cls(
            repository_id=str(raw.get("repository_id") or ""),
            required_analyzers=[str(x) for x in (raw.get("required_analyzers") or [])],
            ran=ran,
            unsupported_languages=[str(x) for x in (raw.get("unsupported_languages") or [])],
            inventory_languages=[str(x) for x in (raw.get("inventory_languages") or [])],
            inventory_projects=[str(x) for x in (raw.get("inventory_projects") or [])],
            patterns_hash=str(raw.get("patterns_hash") or ""),
            status=str(raw.get("status") or "complete"),
            incomplete_reasons=[str(x) for x in (raw.get("incomplete_reasons") or [])],
        )


def _op_count(result: AnalyzerResult) -> int:
    facts = result.extra.get("operation_facts")
    if isinstance(facts, list):
        return len(facts)
    details = result.extra.get("details")
    if isinstance(details, dict):
        ops = details.get("operations")
        if isinstance(ops, list):
            return len(ops)
    iface = result.extra.get("repo_interface")
    if iface is not None and hasattr(iface, "operations"):
        return len(getattr(iface, "operations") or [])
    return 0


def build_coverage_manifest(
    *,
    repository_id: str,
    adapters: list[Analyzer],
    results: list[AnalyzerResult],
    inventory: Inventory,
    unsupported: list[str],
    patterns_hash: str = "",
) -> CoverageManifest:
    """Build manifest from select_analyzers output + extract results."""
    by_id = {a.id: a for a in adapters}
    ran: list[AnalyzerRunRecord] = []
    reasons: list[str] = []
    required = [a.id for a in adapters if a.produces_api_surface]

    result_by_adapter: dict[str, AnalyzerResult] = {}
    for a, res in zip(adapters, results, strict=False):
        result_by_adapter[a.id] = res

    for a in adapters:
        res = result_by_adapter.get(a.id)
        if res is None:
            ran.append(
                AnalyzerRunRecord(
                    analyzer_id=a.id,
                    version=a.version,
                    produces_api_surface=a.produces_api_surface,
                    status="skipped",
                )
            )
            if a.produces_api_surface:
                reasons.append(f"required_analyzer_not_run:{a.id}")
            continue
        if res.error:
            status = "errored"
            if a.produces_api_surface or a.fatal:
                reasons.append(f"analyzer_error:{a.id}:{res.error[:120]}")
            ran.append(
                AnalyzerRunRecord(
                    analyzer_id=a.id,
                    version=a.version,
                    produces_api_surface=a.produces_api_surface,
                    status=status,
                    error=str(res.error),
                    operation_count=0,
                )
            )
            continue
        ops = _op_count(res)
        if a.produces_api_surface and ops == 0:
            reasons.append(f"zero_operations:{a.id}")
        ran.append(
            AnalyzerRunRecord(
                analyzer_id=a.id,
                version=a.version,
                produces_api_surface=a.produces_api_surface,
                status="ran",
                operation_count=ops,
            )
        )

    for lang in unsupported:
        reasons.append(f"unsupported_language:{lang}")

    # Ensure every required id appears
    ran_ids = {r.analyzer_id for r in ran}
    for rid in required:
        if rid not in ran_ids and rid in by_id:
            a = by_id[rid]
            ran.append(
                AnalyzerRunRecord(
                    analyzer_id=a.id,
                    version=a.version,
                    produces_api_surface=True,
                    status="skipped",
                )
            )
            reasons.append(f"required_analyzer_not_run:{rid}")

    status = "incomplete" if reasons else "complete"
    return CoverageManifest(
        repository_id=repository_id,
        required_analyzers=required,
        ran=ran,
        unsupported_languages=list(unsupported),
        inventory_languages=list(inventory.languages),
        inventory_projects=list(inventory.projects),
        patterns_hash=patterns_hash,
        status=status,
        incomplete_reasons=reasons,
    )
