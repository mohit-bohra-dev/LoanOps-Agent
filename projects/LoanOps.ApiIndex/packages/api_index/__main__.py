"""CLI entry for api_index report / health (stubs until later phases)."""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m packages.api_index")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_report = sub.add_parser("report", help="Mismatch report (Phase 2)")
    p_report.add_argument("--env", default="local")
    p_report.add_argument("--json", action="store_true")
    p_health = sub.add_parser("health", help="Health snapshot (Phase 5)")
    p_health.add_argument("--env", default="local")
    p_health.add_argument("--probe", action="store_true")
    args = parser.parse_args(argv)

    if args.cmd == "report":
        payload = {
            "environment": args.env,
            "openapi_only": [],
            "eakg_only": [],
            "ambiguous": [],
            "capabilities_unbound": [],
            "status": "scaffold",
        }
        print(json.dumps(payload, indent=2))
        return 0
    if args.cmd == "health":
        print(json.dumps({"environment": args.env, "apps": {}, "status": "scaffold"}, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
