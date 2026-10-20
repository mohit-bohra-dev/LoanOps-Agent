"""CLI shim: SOP ingest via DocsService (no rag→docs package import).

``loanops-docs`` depends on ``loanops-rag`` (chunker). This module shells out to
``python -m packages.docs.ingest`` so ProjectReference stays acyclic.

Usage:
  uv run python -m packages.rag.ingest data/sops
"""

from __future__ import annotations

import subprocess
import sys


def main() -> None:
    raise SystemExit(
        subprocess.call(
            [sys.executable, "-m", "packages.docs.ingest", *sys.argv[1:]]
        )
    )


if __name__ == "__main__":
    main()
