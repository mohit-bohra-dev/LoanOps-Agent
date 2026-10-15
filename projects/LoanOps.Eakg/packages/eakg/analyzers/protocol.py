"""Analyzer plugin protocol — one class per language/tool."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from packages.eakg.analyzers.types import AnalyzerResult, Inventory

_SKIP_PARTS = frozenset(
    {
        "node_modules",
        ".git",
        ".venv",
        "venv",
        "dist",
        "build",
        "target",
        "bin",
        "obj",
        "__pycache__",
    }
)


def _under_skip(path: Path) -> bool:
    return any(part in _SKIP_PARTS for part in path.parts)


@runtime_checkable
class Analyzer(Protocol):
    """Language or tool adapter selected by inventory + flags."""

    id: str
    version: str
    languages: frozenset[str]
    produces_api_surface: bool
    fatal: bool

    def detect(self, repo: Path) -> float:
        """0.0–1.0 confidence this adapter applies to ``repo``."""

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
        """Extract API facts and/or write engineering artifacts under ``dest``."""


def inventory(repo: Path) -> Inventory:
    """Cheap file-based language list (not a single technology label)."""
    root = Path(repo)
    languages: list[str] = []
    projects: list[str] = []
    csprojs = [p for p in root.rglob("*.csproj") if not _under_skip(p)]
    if csprojs:
        languages.append("csharp")
        for p in csprojs:
            try:
                projects.append(str(p.relative_to(root)).replace("\\", "/"))
            except ValueError:
                projects.append(str(p).replace("\\", "/"))

    pkg_jsons = [p for p in root.rglob("package.json") if not _under_skip(p)]
    if pkg_jsons or (root / "package.json").is_file():
        languages.append("javascript")

    ts_hit = any(
        not _under_skip(p)
        for p in list(root.rglob("*.ts"))[:20] + list(root.rglob("*.tsx"))[:20]
    )
    if ts_hit:
        languages.append("typescript")

    py_markers = (
        list(root.rglob("pyproject.toml"))
        + list(root.rglob("requirements.txt"))
        + list(root.rglob("setup.py"))
    )
    py_markers = [p for p in py_markers if not _under_skip(p)]
    if py_markers or any(
        not _under_skip(p) for p in list(root.rglob("*.py"))[:5]
    ):
        languages.append("python")

    poms = [p for p in root.rglob("pom.xml") if not _under_skip(p)]
    if poms:
        languages.append("java")

    if any(not _under_skip(p) for p in list(root.rglob("*.sql"))[:5]):
        languages.append("sql")

    seen: set[str] = set()
    uniq: list[str] = []
    for lang in languages:
        if lang not in seen:
            seen.add(lang)
            uniq.append(lang)
    return Inventory(languages=uniq, projects=projects[:40])
