#!/usr/bin/env python3
"""Local LoanOps stack helpers: port waits, health probes, ApiIndex refresh.

Usage (from repo root):
  uv run python scripts/dev/stack_ops.py status
  uv run python scripts/dev/stack_ops.py wait --timeout 120
  uv run python scripts/dev/stack_ops.py refresh-index --env dev
  uv run python scripts/dev/stack_ops.py health

Does not start OS processes (GraphDB / MCP / Agent / UI) — use start-stack.ps1.
Never prints secrets.
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

# name -> (host, port, optional HTTP path for probe)
SERVICES: dict[str, tuple[str, int, str | None]] = {
    "postgres": ("127.0.0.1", 5432, None),
    "graphdb": ("127.0.0.1", 7200, "/"),
    "agent_api": ("127.0.0.1", 8000, "/health"),
    "mcp": ("127.0.0.1", 8001, None),  # /ready can be slow; TCP is enough
    "web_ui": ("127.0.0.1", 5173, "/"),
}


def tcp_open(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def http_ok(url: str, timeout: float = 3.0) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = getattr(resp, "status", 200)
            body = resp.read(500).decode("utf-8", errors="replace")
            return 200 <= int(code) < 500, f"{code} {body[:120]}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, type(exc).__name__


def cmd_status(_: argparse.Namespace) -> int:
    rows: dict[str, Any] = {}
    for name, (host, port, path) in SERVICES.items():
        open_ = tcp_open(host, port)
        entry: dict[str, Any] = {"port": port, "tcp": open_}
        if open_ and path:
            ok, detail = http_ok(f"http://{host}:{port}{path}")
            entry["http_ok"] = ok
            entry["detail"] = detail
        rows[name] = entry
        mark = "UP" if open_ else "DOWN"
        print(f"  [{mark}] {name:10} :{port}")
    print(json.dumps(rows, indent=2))
    # Non-zero if core stack down (postgres + mcp + agent)
    core = ("postgres", "mcp", "agent_api")
    return 0 if all(rows[c]["tcp"] for c in core) else 2


def cmd_wait(args: argparse.Namespace) -> int:
    needed = args.services or list(SERVICES.keys())
    deadline = time.time() + float(args.timeout)
    pending = set(needed)
    while pending and time.time() < deadline:
        done: list[str] = []
        for name in sorted(pending):
            host, port, _ = SERVICES[name]
            if tcp_open(host, port):
                print(f"  ready {name} :{port}")
                done.append(name)
        for name in done:
            pending.discard(name)
        if pending:
            time.sleep(1.0)
    if pending:
        print(f"TIMEOUT waiting for: {', '.join(sorted(pending))}", file=sys.stderr)
        return 1
    return 0


def cmd_health(_: argparse.Namespace) -> int:
    """Agent /health + GraphDB + MCP TCP."""
    failures = 0
    for name, (host, port, path) in SERVICES.items():
        if not tcp_open(host, port):
            print(f"FAIL {name}: tcp closed")
            failures += 1
            continue
        if path:
            ok, detail = http_ok(f"http://{host}:{port}{path}")
            print(f"{'OK' if ok else 'FAIL'} {name}: {detail}")
            if not ok:
                failures += 1
        else:
            print(f"OK {name}: tcp open")
    return 1 if failures else 0


def cmd_refresh_index(args: argparse.Namespace) -> int:
    env = args.env
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "packages.api_index.refresh",
        "all",
        "--env",
        env,
    ]
    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), check=False)
    return int(proc.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LoanOps local stack ops (Python).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_status = sub.add_parser("status", help="Print port/HTTP status JSON")
    p_status.set_defaults(func=cmd_status)

    p_wait = sub.add_parser("wait", help="Block until ports are open")
    p_wait.add_argument("--timeout", type=float, default=120.0)
    p_wait.add_argument(
        "--services",
        nargs="*",
        choices=list(SERVICES.keys()),
        default=None,
    )
    p_wait.set_defaults(func=cmd_wait)

    p_health = sub.add_parser("health", help="HTTP/TCP health probes")
    p_health.set_defaults(func=cmd_health)

    p_idx = sub.add_parser("refresh-index", help="ApiIndex refresh all (Bedrock embed)")
    p_idx.add_argument("--env", default="dev")
    p_idx.set_defaults(func=cmd_refresh_index)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
