"""Push approved registry cases into EvalStore datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.common.providers.eval_store import DatasetItem, EvalStoreProvider
from packages.eval.governance.validate import RegistryEntry, load_registry, list_rubric_versions


async def sync_approved(
    store: EvalStoreProvider,
    *,
    data_dir: Path,
) -> dict[str, int]:
    """Upsert approved cases + rubrics into the eval store. Returns counts."""
    registry = [e for e in load_registry(data_dir / "eval" / "registry.jsonl") if e.status == "approved"]
    rubrics = list_rubric_versions(data_dir / "eval" / "rubrics")
    counts = {"datasets": 0, "items": 0, "score_configs": 0}

    for name, version in sorted(rubrics):
        await store.upsert_score_config(name, version)
        counts["score_configs"] += 1

    by_layer: dict[str, list[RegistryEntry]] = {}
    for e in registry:
        by_layer.setdefault(e.layer, []).append(e)

    for layer, entries in by_layer.items():
        ds = f"loanops-l{layer}" if layer != "golden" else "loanops-golden"
        await store.upsert_dataset(ds, description=f"LoanOps layer {layer}")
        counts["datasets"] += 1
        for e in entries:
            await store.upsert_item(
                DatasetItem(
                    id=f"{e.case_id}:{e.layer}:v{e.version}",
                    dataset=ds,
                    input={"case_id": e.case_id, "layer": e.layer},
                    expected_output={"eval_methods": e.eval_methods},
                    metadata={
                        "version": e.version,
                        "status": e.status,
                        "rubric": e.rubric,
                        "rubric_version": e.rubric_version,
                        "source_trace_id": e.source_trace_id,
                    },
                    status=e.status,
                    source_trace_id=e.source_trace_id,
                )
            )
            counts["items"] += 1
    await store.flush()
    return counts
