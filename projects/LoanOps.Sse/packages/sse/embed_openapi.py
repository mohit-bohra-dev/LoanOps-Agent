"""CLI: build OpenAPI operation embedding sidecar.

Thin wrapper over ``python -m packages.api_index.refresh all --sidecar-only``
(spec §9.3). Uses a subprocess so this package does not import ``api_index``
(ProjectReference: api_index → sse, never the reverse).

Usage:
  uv run python -m packages.sse.embed_openapi
"""

from __future__ import annotations

import subprocess
import sys


def main() -> None:
    raise SystemExit(
        subprocess.call(
            [
                sys.executable,
                "-m",
                "packages.api_index.refresh",
                "all",
                "--sidecar-only",
            ]
        )
    )


if __name__ == "__main__":
    main()
