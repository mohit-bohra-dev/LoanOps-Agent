"""Pipeline control plane APIs — catalog, trigger, run history (ADR-033)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from packages.pipelines.runner import (
    PipelineBusyError,
    PipelineNotFoundError,
    create_run,
    dispatch_local,
    get_run,
    list_catalog,
    list_runs,
)
from pydantic import BaseModel

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


class StartRunBody(BaseModel):
    environment: str = "dev"
    repository_id: str | None = None
    sidecar_only: bool = False
    cascade_downstream: bool = False
    triggered_by: str = "anonymous"


class StartRunResponse(BaseModel):
    run_id: str
    pipeline_id: str
    status: str = "queued"


def _log_tail(path: str | None, *, lines: int = 200) -> list[str]:
    if not path:
        return []
    p = Path(path)
    if not p.is_file():
        return []
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return text.splitlines()[-lines:]


@router.get("/catalog")
async def catalog(
    environment: str = Query(default="dev"),
) -> dict[str, Any]:
    return {"pipelines": list_catalog(environment=environment), "environment": environment}


@router.post("/{pipeline_id}/runs", status_code=202, response_model=StartRunResponse)
async def start_run(pipeline_id: str, body: StartRunBody) -> StartRunResponse:
    params: dict[str, Any] = {
        "environment": body.environment,
        "sidecar_only": body.sidecar_only,
        "cascade_downstream": body.cascade_downstream,
    }
    if body.repository_id:
        params["repository_id"] = body.repository_id
    try:
        run_id = create_run(
            pipeline_id,
            params,
            triggered_by=body.triggered_by,
        )
    except PipelineNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"unknown pipeline: {pipeline_id}") from exc
    except PipelineBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    dispatch_local(run_id)
    return StartRunResponse(run_id=run_id, pipeline_id=pipeline_id, status="queued")


@router.get("/runs")
async def runs_list(
    pipeline_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    return {"runs": list_runs(pipeline_id, limit=limit)}


@router.get("/runs/{run_id}")
async def run_detail(run_id: str) -> dict[str, Any]:
    row = get_run(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    out = dict(row)
    out["logs"] = _log_tail(str(row.get("log_path") or "") or None)
    return out
