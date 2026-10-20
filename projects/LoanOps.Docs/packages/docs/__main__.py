"""CLI: ``python -m packages.docs build-links [corpus_root] [out_path]``."""

from __future__ import annotations

import argparse
from pathlib import Path

from packages.docs.link_graph import write_doc_links


def main() -> None:
    parser = argparse.ArgumentParser(description="Docs utilities")
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build-links", help="Build data/docs/doc_links.json")
    build.add_argument(
        "corpus_root",
        nargs="?",
        default="data/sops/_confluence",
        type=Path,
        help="SOP corpus root (default: Confluence cache)",
    )
    build.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("data/docs/doc_links.json"),
        help="Output JSON path",
    )
    args = parser.parse_args()
    if args.cmd == "build-links":
        out = write_doc_links(args.corpus_root, args.out)
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
