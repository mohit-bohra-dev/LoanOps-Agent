"""CLI: execute <run_id> | start <pipeline_id> [--env ...]"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from packages.pipelines.runner import create_run, execute_run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m packages.pipelines")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_exec = sub.add_parser("execute", help="Run a queued ledger row (child / ECS entry)")
    p_exec.add_argument("run_id")

    p_start = sub.add_parser("start", help="Create + execute in foreground (CLI ledger)")
    p_start.add_argument("pipeline_id")
    p_start.add_argument("--env", default="dev")
    p_start.add_argument("--repository-id", default="")
    p_start.add_argument("--sidecar-only", action="store_true")
    p_start.add_argument("--triggered-by", default="cli")

    args = parser.parse_args(argv)

    if args.cmd == "execute":
        result = asyncio.run(execute_run(args.run_id))
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("status") in ("succeeded", "partial") else 1

    params: dict[str, Any] = {
        "environment": args.env,
        "sidecar_only": bool(args.sidecar_only),
    }
    if args.repository_id:
        params["repository_id"] = args.repository_id
    run_id = create_run(
        args.pipeline_id,
        params,
        triggered_by=str(args.triggered_by),
    )
    result = asyncio.run(execute_run(run_id))
    print(json.dumps({"run_id": run_id, **result}, indent=2, default=str))
    return 0 if result.get("status") in ("succeeded", "partial") else 1


if __name__ == "__main__":
    sys.exit(main())
