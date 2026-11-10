"""Declarative pipeline catalog (Phase 1: openapi_to_api_index only)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from packages.api_index.refresh import refresh_all, refresh_app


@dataclass(frozen=True)
class PipelineSpec:
    """One catalog entry: metadata + async entrypoint(params) -> report dict."""

    pipeline_id: str
    title: str
    description: str
    entrypoint: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
    default_params: dict[str, Any] = field(default_factory=dict)


async def _run_openapi_to_api_index(params: dict[str, Any]) -> dict[str, Any]:
    environment = str(params.get("environment") or "dev")
    sidecar_only = bool(params.get("sidecar_only") or False)
    repository_id = params.get("repository_id")
    if repository_id:
        return await refresh_app(
            repository_id=str(repository_id),
            environment=environment,
            sidecar_only=sidecar_only,
        )
    return await refresh_all(environment=environment, sidecar_only=sidecar_only)


PIPELINES: dict[str, PipelineSpec] = {
    "openapi_to_api_index": PipelineSpec(
        pipeline_id="openapi_to_api_index",
        title="OpenAPI + EAKG → ApiIndex Vectors",
        description=(
            "Fetches OpenAPI specs per app, joins with EAKG interfaces, "
            "and embeds callable operations into the vector store."
        ),
        entrypoint=_run_openapi_to_api_index,
        default_params={
            "environment": "dev",
            "repository_id": None,
            "sidecar_only": False,
        },
    ),
}


def get_pipeline(pipeline_id: str) -> PipelineSpec | None:
    return PIPELINES.get(pipeline_id)
