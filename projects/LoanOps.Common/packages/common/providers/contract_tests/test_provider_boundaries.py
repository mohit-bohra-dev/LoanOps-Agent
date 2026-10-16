"""Repo-wide provider boundary gates (ADR-031 lockstep)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[6]  # LoanOps-Agent repo root
PROJECTS = ROOT / "projects"
PROVIDERS_DIR = (
    PROJECTS / "LoanOps.Common" / "packages" / "common" / "providers"
)

_PC_IMPORT = re.compile(r"(?:from|import)\s+provider_contracts\b")
# Config reads only — allow os.environ.copy() for subprocess inheritance (e.g. git).
_ENV_ACCESS = re.compile(r"os\.getenv|os\.environ\s*\[|os\.environ\.get\b")


def _iter_project_py_files() -> list[Path]:
    files: list[Path] = []
    if not PROJECTS.is_dir():
        return files
    for project in PROJECTS.iterdir():
        if not project.is_dir():
            continue
        for py in project.rglob("*.py"):
            files.append(py)
    return files


def test_no_provider_contracts_outside_common_providers() -> None:
    """Domain code must not import provider_contracts directly."""
    allowed_prefix = PROVIDERS_DIR.resolve()
    violations: list[str] = []
    for path in _iter_project_py_files():
        resolved = path.resolve()
        try:
            resolved.relative_to(allowed_prefix)
            continue  # inside packages/common/providers — OK
        except ValueError:
            pass
        # Skip this test file itself if it mentions the pattern in strings only —
        # still scan; pattern is on code lines.
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if _PC_IMPORT.search(line):
                rel = path.relative_to(ROOT)
                violations.append(f"{rel}:{i}: {line.strip()}")
    assert not violations, (
        "provider_contracts imports outside packages/common/providers/:\n"
        + "\n".join(violations)
    )


def test_no_os_environ_outside_settings() -> None:
    """Only settings.py (and tests) may touch os.environ / os.getenv."""
    violations: list[str] = []
    for path in _iter_project_py_files():
        if "tests" in path.parts or path.name.startswith("test_"):
            continue
        if path.name == "settings.py" and "common" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if _ENV_ACCESS.search(line):
                rel = path.relative_to(ROOT)
                violations.append(f"{rel}:{i}: {line.strip()}")
    assert not violations, (
        "os.environ/os.getenv outside settings.py:\n" + "\n".join(violations)
    )


@pytest.mark.parametrize("forbidden", ["langgraph", "openai", "qdrant_client", "presidio"])
def test_domain_packages_do_not_import_provider_sdks(forbidden: str) -> None:
    """Spot-check: banned SDK modules must not appear in domain packages."""
    pattern = re.compile(rf"(?:from|import)\s+{re.escape(forbidden)}\b")
    violations: list[str] = []
    for path in _iter_project_py_files():
        resolved = path.resolve()
        try:
            resolved.relative_to(PROVIDERS_DIR.resolve())
            continue
        except ValueError:
            pass
        if "LoanOps.Common" in path.parts and "providers" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                rel = path.relative_to(ROOT)
                violations.append(f"{rel}:{i}: {line.strip()}")
    assert not violations, f"Forbidden SDK import {forbidden!r}:\n" + "\n".join(violations)
