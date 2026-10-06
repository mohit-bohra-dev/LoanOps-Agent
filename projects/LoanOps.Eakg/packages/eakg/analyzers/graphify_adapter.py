"""Optional Graphify AST extract — not fatal; does not write EAKG operations."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from packages.eakg.analyzers.protocol import Analyzer
from packages.eakg.analyzers.types import AnalyzerResult, GraphFragment

_TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "dotnet.graphifyignore"


class GraphifyAstAdapter:
    id = "graphify_ast"
    version = "1.0.0"
    languages: frozenset[str] = frozenset()
    produces_api_surface = False
    fatal = False

    def detect(self, repo: Path) -> float:
        del repo
        return 1.0 if shutil.which("graphify") else 0.0

    def extract(
        self,
        repo: Path,
        *,
        repository_id: str,
        application_id: str,
        commit_sha: str,
        api_project_path: str = "",
        dest: Path | None = None,
    ) -> AnalyzerResult:
        del application_id, api_project_path
        if dest is None:
            return AnalyzerResult(
                fragment=GraphFragment(),
                error="engineering dest path required",
            )
        tool = shutil.which("graphify")
        if tool is None:
            return AnalyzerResult(
                fragment=GraphFragment(),
                error="graphify CLI not on PATH",
            )
        _ensure_ignore(Path(repo))
        dest.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [
                tool,
                "extract",
                str(Path(repo).resolve()),
                "--code-only",
                "--no-cluster",
                "--out",
                str(dest.resolve()),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "graphify extract failed")[-800:]
            return AnalyzerResult(fragment=GraphFragment(), error=err)
        raw = dest / "graphify-out" / "graph.json"
        if not raw.is_file():
            return AnalyzerResult(
                fragment=GraphFragment(),
                error="graphify extract produced no graph.json",
            )
        target = dest / "graph.json"
        shutil.copy2(raw, target)
        extra: dict[str, object] = {
            "graphify_graph": "engineering/graph.json",
            "commit": commit_sha,
            "repository_id": repository_id,
        }
        return AnalyzerResult(fragment=GraphFragment(), extra=extra)


def _ensure_ignore(repo: Path) -> None:
    dest = repo / ".graphifyignore"
    if dest.is_file() or not _TEMPLATE.is_file():
        return
    dest.write_text(_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")


def as_analyzer() -> Analyzer:
    return GraphifyAstAdapter()
