"""Create / dispatch / execute pipeline runs against the artifact ledger."""

from __future__ import annotations

import logging
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.common.settings import get_settings
from packages.eakg.locks import RepoLock
from packages.eakg.runtime import eakg_runtime
from packages.pipelines.catalog import PIPELINES, get_pipeline

logger = logging.getLogger(__name__)

_ACTIVE = frozenset({"queued", "running"})


class PipelineNotFoundError(KeyError):
    """Unknown pipeline_id."""


class PipelineBusyError(RuntimeError):
    """Another run for this pipeline is already queued or running."""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _arts() -> Any:
    _registry, _store, arts = eakg_runtime()
    arts.ensure_schema()
    return arts


def create_run(
    pipeline_id: str,
    params: dict[str, Any] | None = None,
    *,
    triggered_by: str = "anonymous",
) -> str:
    """Validate pipeline, reject if busy, insert queued row. Returns run_id."""
    spec = get_pipeline(pipeline_id)
    if spec is None:
        raise PipelineNotFoundError(pipeline_id)

    arts = _arts()
    for row in arts.list_pipeline_runs(pipeline_id, limit=20):
        if row.get("status") in _ACTIVE:
            raise PipelineBusyError(
                f"pipeline {pipeline_id} already has active run {row.get('run_id')}"
            )

    merged = {**spec.default_params, **(params or {})}
    run_id = f"run_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
    log_path = str(Path("logs") / "pipelines" / f"{run_id}.log")
    payload: dict[str, Any] = {
        "status": "queued",
        "params": merged,
        "triggered_by": triggered_by,
        "started_at": _now_iso(),
        "finished_at": None,
        "duration_ms": None,
        "report": None,
        "error": None,
        "log_path": log_path,
    }
    arts.put_pipeline_run(run_id, pipeline_id, payload)
    return run_id


def dispatch_local(run_id: str) -> None:
    """Spawn ``python -m packages.pipelines execute <run_id>`` (non-blocking)."""
    arts = _arts()
    row = arts.get_pipeline_run(run_id)
    if row is None:
        raise PipelineNotFoundError(run_id)

    log_path = Path(str(row.get("log_path") or f"logs/pipelines/{run_id}.log"))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("w", encoding="utf-8")
    # Popen: create_subprocess_exec unreliable under uvicorn on Windows.
    subprocess.Popen(  # noqa: S603
        [sys.executable, "-m", "packages.pipelines", "execute", run_id],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=str(Path.cwd()),
    )


async def execute_run(run_id: str) -> dict[str, Any]:
    """Mark running, lock, invoke entrypoint, write terminal status. Child entry."""
    arts = _arts()
    row = arts.get_pipeline_run(run_id)
    if row is None:
        raise PipelineNotFoundError(run_id)

    pipeline_id = str(row.get("pipeline_id") or "")
    spec = get_pipeline(pipeline_id)
    if spec is None:
        raise PipelineNotFoundError(pipeline_id)

    params = dict(row.get("params") or {})
    started = time.perf_counter()
    running = {
        **{k: v for k, v in row.items() if k not in ("run_id", "pipeline_id")},
        "status": "running",
        "started_at": row.get("started_at") or _now_iso(),
    }
    arts.put_pipeline_run(run_id, pipeline_id, running)

    cfg = get_settings()
    lock = RepoLock(
        Path(cfg.eakg.workspace_dir) / ".locks",
        "api_index_refresh",
        timeout_s=30.0,
    )
    try:
        lock.acquire()
    except TimeoutError:
        failed = {
            **running,
            "status": "failed",
            "error": "lock_busy",
            "finished_at": _now_iso(),
            "duration_ms": round((time.perf_counter() - started) * 1000.0, 2),
        }
        arts.put_pipeline_run(run_id, pipeline_id, failed)
        return failed

    try:
        report = await spec.entrypoint(params)
        report_status = str(report.get("status") or "ok")
        if report_status == "ok":
            exec_status = "succeeded"
        elif report_status == "partial":
            exec_status = "partial"
        else:
            exec_status = "failed"
        done: dict[str, Any] = {
            **running,
            "status": exec_status,
            "report": report,
            "error": report.get("error") if exec_status == "failed" else None,
            "finished_at": _now_iso(),
            "duration_ms": round((time.perf_counter() - started) * 1000.0, 2),
        }
        arts.put_pipeline_run(run_id, pipeline_id, done)
        return done
    except Exception as exc:  # noqa: BLE001
        logger.exception("pipeline execute failed run_id=%s", run_id)
        failed = {
            **running,
            "status": "failed",
            "error": str(exc)[:300],
            "finished_at": _now_iso(),
            "duration_ms": round((time.perf_counter() - started) * 1000.0, 2),
        }
        arts.put_pipeline_run(run_id, pipeline_id, failed)
        return failed
    finally:
        lock.release()


def list_catalog() -> list[dict[str, Any]]:
    """Catalog rows with last run (if any)."""
    arts = _arts()
    out: list[dict[str, Any]] = []
    for spec in PIPELINES.values():
        runs = arts.list_pipeline_runs(spec.pipeline_id, limit=1)
        out.append(
            {
                "pipeline_id": spec.pipeline_id,
                "title": spec.title,
                "description": spec.description,
                "default_params": spec.default_params,
                "last_run": runs[0] if runs else None,
            }
        )
    return out


def get_run(run_id: str) -> dict[str, Any] | None:
    row: dict[str, Any] | None = _arts().get_pipeline_run(run_id)
    return row


def list_runs(pipeline_id: str | None = None, *, limit: int = 50) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = _arts().list_pipeline_runs(pipeline_id, limit=limit)
    return rows
