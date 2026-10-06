"""Analyzer plugin protocol — one class per language/tool."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from packages.eakg.analyzers.types import AnalyzerResult, Inventory


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
    csprojs = list(root.rglob("*.csproj"))
    if csprojs:
        languages.append("csharp")
        for p in csprojs:
            try:
                projects.append(str(p.relative_to(root)).replace("\\", "/"))
            except ValueError:
                projects.append(str(p).replace("\\", "/"))
    if (root / "package.json").is_file():
        languages.append("javascript")
    ts_hit = next(root.rglob("*.ts"), None) is not None or next(root.rglob("*.tsx"), None) is not None
    if ts_hit:
        languages.append("typescript")
    if (root / "pyproject.toml").is_file():
        languages.append("python")
    poms = list(root.glob("pom.xml")) or list(root.rglob("pom.xml"))[:1]
    if poms:
        languages.append("java")
    if next(root.rglob("*.sql"), None) is not None:
        languages.append("sql")
    # unique preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for lang in languages:
        if lang not in seen:
            seen.add(lang)
            uniq.append(lang)
    return Inventory(languages=uniq, projects=projects[:40])
