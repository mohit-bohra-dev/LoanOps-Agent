#!/usr/bin/env python3
"""Generate synthetic multi-app OpenAPI + registry + discovery benchmark (spec §14.2).

Default: 30 apps × ~170 ops ≈ 5.1k operations, seed 42.
No PII — synthetic domain vocabulary only.

Examples:
  uv run python scripts/fixtures/gen_scale_fixture.py
  uv run python scripts/fixtures/gen_scale_fixture.py --apps 5 --ops-per-app 20 --out-dir data/eakg/fixtures/scale
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

# Synthetic domain vocabulary (no real loan/customer data).
_DOMAINS = (
    "fees",
    "escrow",
    "payment",
    "schedule",
    "balance",
    "tax",
    "insurance",
    "document",
    "statement",
    "disbursement",
    "modification",
    "forbearance",
    "impound",
    "hazard",
    "flood",
    "appraisal",
    "title",
    "closing",
    "servicing",
    "transfer",
)
_ACTIONS = (
    "get",
    "list",
    "search",
    "find",
    "lookup",
    "fetch",
    "query",
    "read",
    "check",
    "status",
)
_ENTITIES = (
    "Loan",
    "Account",
    "Item",
    "Record",
    "Detail",
    "Summary",
    "History",
    "Event",
    "Batch",
    "Report",
)


def _app_id(i: int) -> str:
    return f"scaleapp{i:02d}"


def _app_label(i: int) -> str:
    domain = _DOMAINS[i % len(_DOMAINS)]
    return f"Scale {domain.title()} App {i:02d}"


def _operation_id(rng: random.Random, app_i: int, op_i: int, *, shared_name: str | None) -> str:
    if shared_name:
        return shared_name
    action = _ACTIONS[(app_i + op_i) % len(_ACTIONS)]
    entity = _ENTITIES[(app_i * 3 + op_i) % len(_ENTITIES)]
    domain = _DOMAINS[(app_i + op_i) % len(_DOMAINS)]
    # Deterministic but varied; include index for uniqueness within app.
    return f"{action}{domain.title()}{entity}{op_i}"


def _build_spec(
    rng: random.Random,
    app_i: int,
    ops_per_app: int,
    shared_names: list[str],
) -> dict[str, object]:
    app_id = _app_id(app_i)
    paths: dict[str, object] = {}
    # First N shared_names appear as same operationId across apps (cross-app collision).
    for op_i in range(ops_per_app):
        shared = shared_names[op_i] if op_i < len(shared_names) else None
        op_id = _operation_id(rng, app_i, op_i, shared_name=shared)
        domain = _DOMAINS[(app_i + op_i) % len(_DOMAINS)]
        path = f"/api/{app_id}/{domain}/{{id}}/v{op_i}"
        if shared:
            # Same path suffix + operationId across apps for collision pairs.
            path = f"/api/shared/{shared}/{{id}}"
        paths[path] = {
            "get": {
                "operationId": op_id,
                "summary": f"Synthetic {op_id} for {app_id}",
                "tags": [domain, app_id],
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {"200": {"description": "ok"}},
            }
        }
    return {
        "openapi": "3.0.3",
        "info": {
            "title": f"{_app_label(app_i)} (synthetic)",
            "version": "1.0.0",
            "description": "Synthetic scale fixture — no production data",
        },
        "servers": [{"url": f"http://127.0.0.1:{9200 + app_i}"}],
        "paths": paths,
    }


def _build_registry(
    apps: int,
    specs_rel: Path,
) -> dict[str, object]:
    repos: list[dict[str, object]] = []
    for i in range(apps):
        app_id = _app_id(i)
        repos.append(
            {
                "repository_id": app_id,
                "application": _app_label(i),
                "application_id": app_id,
                "git_url": f"https://example.invalid/scale/{app_id}.git",
                "default_branch": "main",
                "gitlab_project_id": 90000 + i,
                "team": "synthetic/scale",
                "owner": "synthetic/scale",
                "technology": "dotnet-aspnetcore",
                "index_status": "indexed",
                "access_status": "ok",
                "visibility": "private",
                "deployables": [f"{app_id}.Api"],
                "shard_path": f"repos/{app_id}",
                "api_project_path": f"src/{app_id}.Api",
                "service_url_key": f"{app_id}Url",
                "environments": {
                    "local": {
                        "base_url": f"http://127.0.0.1:{9200 + i}",
                        "spec_fixture": str(specs_rel / f"{app_id}.openapi.json").replace(
                            "\\", "/"
                        ),
                    }
                },
            }
        )
    return {"repositories": repos}


def _build_benchmark(
    rng: random.Random,
    apps: int,
    ops_per_app: int,
    shared_names: list[str],
    *,
    questions: int,
) -> list[dict[str, object]]:
    """≥100 questions when questions>=100; synthetic vocabulary; cross-app pairs."""
    rows: list[dict[str, object]] = []
    # Cross-app same-name questions (≥10 pairs when shared_names long enough).
    for name in shared_names:
        for app_i in range(min(apps, 3)):
            rows.append(
                {
                    "id": f"xapp-{name}-{_app_id(app_i)}",
                    "query": f"call {name} on {_app_label(app_i)}",
                    "expected_public_ids": [f"{_app_id(app_i)}:{name}"],
                    "application_id": _app_id(app_i),
                    "kind": "cross_app_same_name",
                }
            )
    # Per-app unique op questions.
    while len(rows) < questions:
        app_i = rng.randrange(apps)
        op_i = rng.randrange(ops_per_app)
        if op_i < len(shared_names):
            continue
        op_id = _operation_id(rng, app_i, op_i, shared_name=None)
        domain = _DOMAINS[(app_i + op_i) % len(_DOMAINS)]
        rows.append(
            {
                "id": f"q-{_app_id(app_i)}-{op_i}",
                "query": f"{_ACTIONS[op_i % len(_ACTIONS)]} {domain} {_ENTITIES[op_i % len(_ENTITIES)].lower()} for {_app_label(app_i)}",
                "expected_public_ids": [f"{_app_id(app_i)}:{op_id}"],
                "application_id": _app_id(app_i),
                "kind": "unique",
            }
        )
    return rows[:questions]


def generate(
    *,
    apps: int,
    ops_per_app: int,
    seed: int,
    out_dir: Path,
    questions: int,
    cross_app_pairs: int,
) -> dict[str, object]:
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    specs_dir = out_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    shared_names = [f"getSharedResource{i}" for i in range(cross_app_pairs)]

    for i in range(apps):
        spec = _build_spec(rng, i, ops_per_app, shared_names)
        path = specs_dir / f"{_app_id(i)}.openapi.json"
        path.write_text(json.dumps(spec, indent=2), encoding="utf-8")

    # Spec fixture paths relative to repo root.
    try:
        repo_root = Path(__file__).resolve().parents[2]
        specs_rel = specs_dir.relative_to(repo_root)
    except ValueError:
        specs_rel = specs_dir

    registry = _build_registry(apps, specs_rel)
    reg_path = out_dir / "repositories.yaml"
    try:
        import yaml

        reg_path.write_text(
            yaml.safe_dump(registry, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    except ImportError:
        # Fallback JSON if PyYAML unavailable in bare interpreter.
        reg_path = out_dir / "repositories.json"
        reg_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    bench = _build_benchmark(
        rng, apps, ops_per_app, shared_names, questions=questions
    )
    bench_path = out_dir / "api_discovery_benchmark.jsonl"
    # Also write canonical eval path when generating the default full suite.
    with bench_path.open("w", encoding="utf-8") as fh:
        for row in bench:
            fh.write(json.dumps(row) + "\n")

    eval_dir = Path("data/eval")
    if apps >= 30 and ops_per_app >= 100:
        eval_dir.mkdir(parents=True, exist_ok=True)
        canon = eval_dir / "api_discovery_benchmark.jsonl"
        with canon.open("w", encoding="utf-8") as fh:
            for row in bench:
                fh.write(json.dumps(row) + "\n")

    meta = {
        "apps": apps,
        "ops_per_app": ops_per_app,
        "operations": apps * ops_per_app,
        "seed": seed,
        "questions": len(bench),
        "cross_app_pairs": cross_app_pairs,
        "out_dir": str(out_dir),
        "registry": str(reg_path),
        "benchmark": str(bench_path),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apps", type=int, default=30)
    parser.add_argument("--ops-per-app", type=int, default=170)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/eakg/fixtures/scale"),
    )
    parser.add_argument("--questions", type=int, default=120)
    parser.add_argument("--cross-app-pairs", type=int, default=12)
    args = parser.parse_args(argv)
    meta = generate(
        apps=args.apps,
        ops_per_app=args.ops_per_app,
        seed=args.seed,
        out_dir=args.out_dir,
        questions=args.questions,
        cross_app_pairs=args.cross_app_pairs,
    )
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
