"""Per-app health aggregation for /ready (spec §5.2 / §9.5)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from packages.api_index.catalog import mismatch_report
from packages.api_index.indexer import load_manifest
from packages.api_index.paths import manifest_path
from packages.api_index.records import OperationSet
from packages.common.providers.credential_broker import AbstractCredentialBroker
from packages.common.settings import Settings
from packages.eakg.registry import RepositoryRecord, RepositoryRegistry
from packages.eakg.registry_validate import RegistryIssue, validate_registry
from packages.eakg.spec_cache import read_pointer
from packages.eakg.store import ShardStore
from packages.sse.invoke_outcomes import LastInvokeRing
from packages.sse.types import BreakerRegistry

CredentialState = Literal["configured", "missing", "error"]


class AppHealth(BaseModel):
    application_id: str
    lifecycle: str = "active"
    indexed: bool = False
    operation_count: int = 0
    spec_fetched_at: str | None = None
    spec_age_hours: float | None = None
    stale: bool = False
    spec_status: str = "missing"
    credential: CredentialState = "missing"
    last_invoke: dict[str, str] | None = None
    breaker: str = "closed"
    issues: list[str] = Field(default_factory=list)


class HealthSnapshot(BaseModel):
    status: str = "ready"
    environment: str
    catalog: dict[str, Any] = Field(default_factory=dict)
    index: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, int] = Field(default_factory=dict)
    apps: list[AppHealth] = Field(default_factory=list)
    catalog_health: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


def _parse_fetched_at(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _breaker_state(breaker: BreakerRegistry | None, application_id: str) -> str:
    if breaker is None:
        return "closed"
    state_of = getattr(breaker, "state_of", None)
    if callable(state_of):
        return str(state_of(application_id))
    return "open" if breaker.is_open(application_id) else "closed"


def _issue_codes(
    record: RepositoryRecord,
    environment: str,
    issues: dict[str, list[RegistryIssue]],
) -> list[str]:
    codes: list[str] = []
    for issue in issues.get(record.application_id, []):
        if issue.environment in (None, environment):
            codes.append(issue.code)
    return codes


class AppHealthService:
    """Merge registry, specs, index coverage, broker, last invoke, breaker."""

    def __init__(
        self,
        *,
        settings: Settings,
        registry: RepositoryRegistry | None = None,
        store: ShardStore | None = None,
        op_set: OperationSet | None = None,
        credentials: AbstractCredentialBroker | None = None,
        breaker: BreakerRegistry | None = None,
        invoke_ring: LastInvokeRing | None = None,
        capabilities: Any | None = None,
    ) -> None:
        self._settings = settings
        self._registry = registry or RepositoryRegistry(settings.eakg.registry_path)
        self._store = store or ShardStore(settings.eakg.shard_dir)
        self._op_set = op_set
        self._credentials = credentials
        self._breaker = breaker
        self._invoke_ring = invoke_ring or LastInvokeRing()
        self._capabilities = capabilities

    async def snapshot(self, *, environment: str | None = None) -> HealthSnapshot:
        env = environment or self._settings.eakg.environment
        stale_after = float(self._settings.api_index.stale_after_hours)
        warnings: list[str] = []
        now = datetime.now(UTC)

        registry_issues = validate_registry(self._registry)
        records = [
            r
            for r in self._registry.list()
            if r.lifecycle != "retired"
            and env in r.environments
            and r.environments[env].enabled
        ]

        ops_by_app: dict[str, int] = {}
        built_at = ""
        if self._op_set is not None:
            raw_built = self._op_set.built_at
            built_at = (
                raw_built.isoformat()
                if hasattr(raw_built, "isoformat")
                else str(raw_built or "")
            )
            for op in self._op_set.operations:
                ops_by_app[op.application_id] = ops_by_app.get(op.application_id, 0) + 1

        manifest = load_manifest(
            Path(manifest_path(self._settings.eakg.shard_dir, env))
        )
        indexed_apps: set[str] = {
            e.application_id for e in manifest.entries.values() if e.application_id
        }
        total_ops = sum(ops_by_app.values())
        indexed_ops = len(manifest.entries)
        coverage = (
            round(indexed_ops / total_ops, 3) if total_ops > 0 else 0.0
        )
        if not manifest.namespace and total_ops > 0:
            warnings.append("vector_store_unavailable")

        apps: list[AppHealth] = []
        healthy = 0
        degraded = 0
        for record in sorted(records, key=lambda r: r.application_id):
            app_id = record.application_id
            pointer = read_pointer(self._store, record.repository_id, env) or {}
            fetched_at = str(pointer.get("fetched_at") or "") or None
            fetched_dt = _parse_fetched_at(fetched_at)
            age_hours: float | None = None
            stale = False
            if fetched_dt is not None:
                age_hours = round((now - fetched_dt.astimezone(UTC)).total_seconds() / 3600.0, 2)
                stale = age_hours > stale_after
            spec_status = str(pointer.get("status") or "missing")
            op_count = ops_by_app.get(app_id, 0)
            is_indexed = app_id in indexed_apps and op_count > 0

            credential: CredentialState = "missing"
            if self._credentials is not None:
                audience = record.environments[env].auth_audience or ""
                try:
                    check = await self._credentials.check(app_id, audience)
                    if check.state in ("configured", "missing", "error"):
                        credential = check.state
                except Exception:  # noqa: BLE001
                    credential = "error"
            else:
                cred_raw = pointer.get("credential")
                if cred_raw == "configured":
                    credential = "configured"
                elif cred_raw == "missing":
                    credential = "missing"
                elif cred_raw == "error":
                    credential = "error"

            last_invoke = (
                self._invoke_ring.as_dict(app_id) if self._invoke_ring else None
            )
            issues = _issue_codes(record, env, registry_issues)
            if last_invoke:
                outcome = last_invoke.get("outcome")
                if outcome == "no_access":
                    issues.append("access_denied")
                elif outcome == "unavailable":
                    issues.append("unreachable")

            app = AppHealth(
                application_id=app_id,
                lifecycle=record.lifecycle,
                indexed=is_indexed,
                operation_count=op_count,
                spec_fetched_at=fetched_at,
                spec_age_hours=age_hours,
                stale=stale,
                spec_status=spec_status,
                credential=credential,
                last_invoke=last_invoke,
                breaker=_breaker_state(self._breaker, app_id),
                issues=issues,
            )
            apps.append(app)
            is_degraded = (
                stale
                or not is_indexed
                or spec_status == "failed"
                or credential in ("missing", "error")
                or bool(issues)
                or app.breaker == "open"
            )
            if is_degraded:
                degraded += 1
            else:
                healthy += 1

        catalog_health: dict[str, Any] = {
            "openapi_only": 0,
            "eakg_only": 0,
            "ambiguous": 0,
            "capabilities_unbound": 0,
        }
        if self._op_set is not None:
            report = mismatch_report(self._op_set, self._capabilities)
            catalog_health = {
                "openapi_only": len(report["openapi_only"]),
                "eakg_only": len(report["eakg_only"]),
                "ambiguous": len(report["ambiguous"]),
                "capabilities_unbound": len(report["capabilities_unbound"]),
            }

        return HealthSnapshot(
            status="ready",
            environment=env,
            catalog={
                "operations": total_ops,
                "built_at": built_at,
                "source": "registry",
            },
            index={
                "backend": "vector_store" if manifest.namespace else "none",
                "namespace": manifest.namespace,
                "coverage": coverage,
            },
            summary={
                "apps": len(apps),
                "healthy": healthy,
                "degraded": degraded,
            },
            apps=apps,
            catalog_health=catalog_health,
            warnings=warnings,
        )
