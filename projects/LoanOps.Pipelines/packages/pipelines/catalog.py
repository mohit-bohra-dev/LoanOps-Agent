"""Declarative pipeline catalog (ADR-033)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from packages.api_index.catalog import load_operations, mismatch_report
from packages.api_index.refresh import refresh_all, refresh_app
from packages.common.providers.factory import get_embedding_provider
from packages.common.settings import get_settings
from packages.eakg.runtime import eakg_runtime


@dataclass(frozen=True)
class PipelineSpec:
    """One catalog entry: metadata + async entrypoint(params) -> report dict."""

    pipeline_id: str
    title: str
    description: str
    entrypoint: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
    default_params: dict[str, Any] = field(default_factory=dict)
    downstream: tuple[str, ...] = ()
    long_running: bool = False


async def _run_openapi_to_api_index(params: dict[str, Any]) -> dict[str, Any]:
    environment = str(params.get("environment") or "dev")
    sidecar_only = bool(params.get("sidecar_only") or False)
    repository_id = params.get("repository_id")
    if repository_id:
        report = await refresh_app(
            repository_id=str(repository_id),
            environment=environment,
            sidecar_only=sidecar_only,
        )
    else:
        report = await refresh_all(environment=environment, sidecar_only=sidecar_only)

    # Quality: mismatch_report against written OperationSet.
    quality_status = "skipped"
    quality: dict[str, Any] = {}
    try:
        cfg = get_settings()
        _registry, store, _arts = eakg_runtime(cfg)
        op_set = load_operations(store.root, environment)
        if op_set is not None:
            quality = mismatch_report(op_set)
            ambiguous = quality.get("ambiguous") or []
            unbound = quality.get("capabilities_unbound") or []
            quality_status = "warning" if ambiguous or unbound else "passed"
    except Exception as exc:  # noqa: BLE001
        quality = {"error": str(exc)[:200]}
        quality_status = "skipped"

    report = dict(report)
    report["quality_status"] = quality_status
    report["quality"] = {
        "openapi_only_count": len(quality.get("openapi_only") or []),
        "eakg_only_count": len(quality.get("eakg_only") or []),
        "ambiguous_count": len(quality.get("ambiguous") or []),
        "capabilities_unbound_count": len(quality.get("capabilities_unbound") or []),
        **(
            {"error": quality["error"]}
            if "error" in quality
            else {}
        ),
    }

    # Persist asset hashes for freshness badges.
    try:
        from packages.pipelines.freshness import (
            hashes_from_operations_file,
            store_api_index_hashes,
        )

        hashes = hashes_from_operations_file(environment)
        if hashes is not None:
            _r, _s, arts = eakg_runtime()
            store_api_index_hashes(arts, environment, hashes)
    except Exception:  # noqa: BLE001
        pass

    return report


async def _run_eakg_sync_nightly(params: dict[str, Any]) -> dict[str, Any]:
    from packages.eakg.sync import sync_nightly

    _ = params
    report = await sync_nightly()
    return {"status": "ok", **{k: v for k, v in report.items()}}


async def _run_code_to_eakg(params: dict[str, Any]) -> dict[str, Any]:
    from packages.eakg.sync import sync_repo

    repository_id = str(params.get("repository_id") or "").strip()
    if not repository_id:
        return {"status": "failed", "error": "repository_id required"}
    report = await sync_repo(repository_id)
    return {"status": "ok", "repository_id": repository_id, **report}


async def _run_capability_embeddings(params: dict[str, Any]) -> dict[str, Any]:
    from packages.eakg.embed import embed_from_settings

    _ = params
    embedder = get_embedding_provider()

    async def _embed(text: str) -> list[float]:
        emb = await embedder.embed(text)
        return list(emb.vector)

    path = await embed_from_settings(_embed)
    return {"status": "ok", "path": str(path)}


async def _run_sop_to_doc_embeddings(params: dict[str, Any]) -> dict[str, Any]:
    from packages.docs.ingest import ingest_default

    _ = params
    try:
        n = await ingest_default()
    except FileNotFoundError as exc:
        return {"status": "failed", "error": str(exc)[:300]}
    return {"status": "ok", "chunks_indexed": n}


async def _run_sop_to_graphrag(params: dict[str, Any]) -> dict[str, Any]:
    from packages.graph_rag.build import build_and_index

    cfg = get_settings()
    doc_links = Path(str(params.get("doc_links") or "data/docs/doc_links.json"))
    corpus = Path(str(params.get("corpus") or cfg.data.confluence.artifact_dir or "data/sops/_confluence"))
    artifact_dir = Path(str(params.get("artifact_dir") or "data/graphrag"))
    extract = bool(params.get("extract") or False)
    rebuild = bool(params.get("rebuild") or False)
    n = await build_and_index(
        doc_links_path=doc_links,
        corpus_root=corpus,
        artifact_dir=artifact_dir,
        extract=extract,
        write_repo_artifact=True,
        rebuild=rebuild,
    )
    return {"status": "ok", "communities": n}


async def _run_code_to_engineering_kg(params: dict[str, Any]) -> dict[str, Any]:
    """Re-onboard one repo with engineering_graph=True (Graphify AST + links)."""
    from packages.eakg.onboard import onboard_repository
    from packages.eakg.runtime import eakg_runtime as rt

    repository_id = str(params.get("repository_id") or "").strip()
    if not repository_id:
        return {"status": "failed", "error": "repository_id required"}
    cfg = get_settings()
    registry, store, _arts = rt(cfg)
    rec = registry.get(repository_id)
    if rec is None:
        return {"status": "failed", "error": f"unknown repository: {repository_id}"}
    local = Path(cfg.eakg.workspace_dir) / repository_id
    report = await onboard_repository(
        registry,
        store,
        rec,
        settings=cfg,
        local_path=local if local.is_dir() else None,
        run_semantic=False,
        engineering_graph=True,
    )
    return {"status": "ok", "repository_id": repository_id, **report}


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
    "eakg_sync_nightly": PipelineSpec(
        pipeline_id="eakg_sync_nightly",
        title="EAKG nightly sync",
        description="Spec refresh, onboard changed repos, cross-app rebuild, publish catalog.",
        entrypoint=_run_eakg_sync_nightly,
        default_params={},
        downstream=("openapi_to_api_index", "eakg_to_capability_embeddings"),
        long_running=True,
    ),
    "code_to_eakg": PipelineSpec(
        pipeline_id="code_to_eakg",
        title="Code → EAKG (one repo)",
        description=(
            "Clone/extract one registered repository into EAKG. Long-running "
            "(git + Roslyn/regex)."
        ),
        entrypoint=_run_code_to_eakg,
        default_params={"repository_id": None},
        long_running=True,
    ),
    "eakg_to_capability_embeddings": PipelineSpec(
        pipeline_id="eakg_to_capability_embeddings",
        title="EAKG → capability embeddings",
        description="Embed capability text from GraphDB/shards into the embeddings store.",
        entrypoint=_run_capability_embeddings,
        default_params={},
    ),
    "sop_to_doc_embeddings": PipelineSpec(
        pipeline_id="sop_to_doc_embeddings",
        title="SOP → doc embeddings",
        description="Ingest Confluence/file SOP corpus into the docs vector namespace.",
        entrypoint=_run_sop_to_doc_embeddings,
        default_params={},
        downstream=("sop_to_graphrag",),
    ),
    "sop_to_graphrag": PipelineSpec(
        pipeline_id="sop_to_graphrag",
        title="SOP → GraphRAG",
        description="Build document communities and index summary vectors.",
        entrypoint=_run_sop_to_graphrag,
        default_params={
            "doc_links": "data/docs/doc_links.json",
            "extract": False,
            "rebuild": False,
        },
    ),
    "code_to_engineering_kg": PipelineSpec(
        pipeline_id="code_to_engineering_kg",
        title="Code → Engineering KG",
        description=(
            "Onboard one repo with Graphify engineering graph + operation links. "
            "Long-running."
        ),
        entrypoint=_run_code_to_engineering_kg,
        default_params={"repository_id": None},
        long_running=True,
    ),
}


def get_pipeline(pipeline_id: str) -> PipelineSpec | None:
    return PIPELINES.get(pipeline_id)
