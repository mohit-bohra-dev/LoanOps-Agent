#!/usr/bin/env python3
"""Fail if a workspace project imports packages.* / apps.* without a loanops-* dep.

Also enforces provider_contracts lockstep: only loanops-common may depend on
provider-contracts; domain projects may only use an allowlisted set of
third-party (non-provider-SDK) dependencies.

Mirrors .csproj ProjectReference checks for the uv workspace.
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "projects"

# Import prefix -> loanops distribution name
PKG_TO_DIST: dict[str, str] = {
    "common": "loanops-common",
    "safety": "loanops-safety",
    "db": "loanops-db",
    "wiki": "loanops-wiki",
    "rag": "loanops-rag",
    "docs": "loanops-docs",
    "graph_rag": "loanops-graphrag",
    "sse": "loanops-sse",
    "capability_kg": "loanops-capability-kg",
    "eakg": "loanops-eakg",
    "api_index": "loanops-api-index",
    "pipelines": "loanops-pipelines",
    "tools": "loanops-tools",
    "agent_core": "loanops-agent-core",
    "mcp_server": "loanops-mcp-server",
    "eval": "loanops-eval",
}

APP_TO_DIST: dict[str, str] = {
    "agent_api": "loanops-agent-api",
}

_DEP_NAME = re.compile(r"^([A-Za-z0-9_.-]+)")

# Domain/transport libs OK outside Common. Provider SDKs are NOT listed here.
_DOMAIN_THIRD_PARTY_ALLOW: frozenset[str] = frozenset(
    {
        "fastapi",
        "uvicorn",
        "mcp",
        "httpx",
        "aioodbc",
        "networkx",
        "rdflib",
        "pyyaml",
        "tree-sitter",
        "tree-sitter-javascript",
        "tree-sitter-typescript",
        "tree-sitter-python",
        "markitdown",
        "ragas",
        "numpy",
        "pydantic",
        "pydantic-settings",
    }
)

# Banned provider SDKs / engines — must go through provider_contracts.
_PROVIDER_SDK_BAN: frozenset[str] = frozenset(
    {
        "provider-contracts",
        "langgraph",
        "langchain",
        "langchain-core",
        "openai",
        "anthropic",
        "google-genai",
        "aioboto3",
        "boto3",
        "qdrant-client",
        "sentence-transformers",
        "presidio-analyzer",
        "presidio-anonymizer",
        "redis",
        "asyncpg",
        "pgvector",
        "sqlalchemy",
        "agent-framework",
        "langfuse",
    }
)


def _dep_names(raw: list[str]) -> set[str]:
    out: set[str] = set()
    for item in raw:
        m = _DEP_NAME.match(item.strip())
        if m:
            out.add(m.group(1).lower().replace("_", "-"))
    return out


def _imports_in_file(path: Path) -> set[str]:
    """Return package/app short names imported from packages.* / apps.*."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            if parts[0] == "packages" and len(parts) >= 2:
                found.add(parts[1])
            elif parts[0] == "apps" and len(parts) >= 2:
                found.add(f"apps.{parts[1]}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == "packages" and len(parts) >= 2:
                    found.add(parts[1])
                elif parts[0] == "apps" and len(parts) >= 2:
                    found.add(f"apps.{parts[1]}")
    return found


def _owned_pkg(project_dir: Path) -> str | None:
    pkgs = project_dir / "packages"
    if pkgs.is_dir():
        kids = [p.name for p in pkgs.iterdir() if p.is_dir() and not p.name.startswith(".")]
        if len(kids) == 1:
            return kids[0]
    apps = project_dir / "apps"
    if apps.is_dir():
        kids = [p.name for p in apps.iterdir() if p.is_dir() and not p.name.startswith(".")]
        if len(kids) == 1:
            return f"apps.{kids[0]}"
    return None


def check_third_party_allowlist(project_dir: Path, deps: set[str], dist_name: str) -> list[str]:
    """Enforce provider_contracts lockstep on pyproject dependencies."""
    errors: list[str] = []
    is_common = dist_name == "loanops-common"
    for dep in sorted(deps):
        if dep.startswith("loanops-"):
            continue
        if dep == "provider-contracts":
            if not is_common:
                errors.append(
                    f"{project_dir.name}: only loanops-common may depend on "
                    f"provider-contracts (found in {dist_name}). Add adapters in "
                    "provider_contracts + packages/common/providers/ instead."
                )
            continue
        if dep in _PROVIDER_SDK_BAN and not is_common:
            errors.append(
                f"{project_dir.name}: banned provider SDK {dep!r} — add it to "
                "provider_contracts (ABC + concrete + mock + extra) and expose via "
                "LoanOps.Common factory first."
            )
            continue
        if not is_common and dep not in _DOMAIN_THIRD_PARTY_ALLOW and dep not in _PROVIDER_SDK_BAN:
            # Unknown third-party: allow if clearly domain; otherwise warn as error
            # for lockstep discipline. Common may pull anything via provider extras.
            errors.append(
                f"{project_dir.name}: third-party dep {dep!r} is not on the domain "
                "allowlist in scripts/check_project_refs.py. If it is a provider SDK, "
                "put it in provider_contracts; if domain/transport, add it to "
                "_DOMAIN_THIRD_PARTY_ALLOW."
            )
    return errors


def check_project(project_dir: Path) -> list[str]:
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.is_file():
        return []
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    deps = _dep_names(list(data.get("project", {}).get("dependencies", [])))
    owned = _owned_pkg(project_dir)
    dist_name = str(data.get("project", {}).get("name") or "")
    errors: list[str] = []
    errors.extend(check_third_party_allowlist(project_dir, deps, dist_name))

    for py in project_dir.rglob("*.py"):
        if "tests" in py.parts or py.name.startswith("test_"):
            continue
        for name in _imports_in_file(py):
            if owned and (name == owned or name == owned.removeprefix("apps.")):
                continue
            if name.startswith("apps."):
                dist = APP_TO_DIST.get(name.split(".", 1)[1])
            else:
                dist = PKG_TO_DIST.get(name)
            if dist is None:
                continue
            if dist not in deps and dist != data.get("project", {}).get("name"):
                if owned == name or owned == f"apps.{name}":
                    continue
                rel = py.relative_to(ROOT)
                errors.append(
                    f"{rel}: imports {name!r} but {project_dir.name} "
                    f"does not declare dependency {dist!r}"
                )
    return errors


def main() -> int:
    if not PROJECTS.is_dir():
        print("projects/ missing", file=sys.stderr)
        return 2
    all_errors: list[str] = []
    for project_dir in sorted(PROJECTS.iterdir()):
        if not project_dir.is_dir():
            continue
        all_errors.extend(check_project(project_dir))
    if all_errors:
        print("ProjectReference check failed:\n" + "\n".join(all_errors), file=sys.stderr)
        return 1
    print(f"OK — checked {len(list(PROJECTS.iterdir()))} projects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
