"""Invoke Roslyn-based .NET controller extractor (tools/eakg-dotnet-extract)."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from packages.eakg.models import ApiOperationFact, AuthzSource, Evidence

logger = logging.getLogger(__name__)

DETECTOR_ID = "dotnet_roslyn"
DETECTOR_VERSION = "2.0.0"


def _loanops_repo_root() -> Path:
    """Find LoanOps-Agent root (uv install copies eakg into site-packages)."""
    marker = Path("tools") / "eakg-dotnet-extract" / "EakgDotnetExtract.csproj"
    cwd = Path.cwd()
    if (cwd / marker).is_file():
        return cwd
    try:
        git = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(cwd),
        )
        if git.returncode == 0:
            root = Path(git.stdout.strip())
            if (root / marker).is_file():
                return root
    except OSError:
        pass
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / marker).is_file():
            return parent
    return cwd


def _tool_proj() -> Path:
    return _loanops_repo_root() / "tools" / "eakg-dotnet-extract" / "EakgDotnetExtract.csproj"


def _tool_dll() -> Path:
    return (
        _loanops_repo_root()
        / "tools"
        / "eakg-dotnet-extract"
        / "bin"
        / "Release"
        / "net8.0"
        / "eakg-dotnet-extract.dll"
    )


def roslyn_tool_available() -> bool:
    if shutil.which("dotnet") is None:
        return False
    return _tool_proj().is_file()


def _run_extractor(
    repo_root: Path,
    *,
    repository_id: str,
    commit_sha: str,
    api_project_path: str,
) -> dict[str, Any]:
    if not roslyn_tool_available():
        raise RuntimeError("dotnet SDK or eakg-dotnet-extract project missing")

    args = [
        "--repo",
        str(repo_root.resolve()),
        "--repo-id",
        repository_id,
        "--commit",
        commit_sha,
    ]
    if api_project_path:
        args.extend(["--api-project-path", api_project_path])

    tool_proj = _tool_proj()
    tool_dll = _tool_dll()
    if tool_dll.is_file():
        cmd = ["dotnet", "exec", str(tool_dll), *args]
    else:
        cmd = [
            "dotnet",
            "run",
            "--project",
            str(tool_proj),
            "-c",
            "Release",
            "--no-build",
            "--",
            *args,
        ]
        # Ensure build once if dll missing
        build = subprocess.run(
            ["dotnet", "build", str(tool_proj), "-c", "Release", "-v", "q"],
            capture_output=True,
            text=True,
            check=False,
        )
        if build.returncode != 0:
            raise RuntimeError(f"roslyn tool build failed: {build.stderr[-500:]}")
        if tool_dll.is_file():
            cmd = ["dotnet", "exec", str(tool_dll), *args]
        else:
            cmd = [
                "dotnet",
                "run",
                "--project",
                str(tool_proj),
                "-c",
                "Release",
                "--",
                *args,
            ]

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            f"roslyn extract failed ({proc.returncode}): {proc.stderr[-800:] or proc.stdout[-800:]}"
        )
    raw = proc.stdout.strip()
    if not raw:
        raise RuntimeError("roslyn extract returned empty stdout")
    # Last JSON object if build noise preceded (should not with exec)
    line = raw.splitlines()[-1]
    data = json.loads(line)
    if not isinstance(data, dict):
        raise RuntimeError("roslyn extract JSON root must be object")
    return data


def extract_controllers_roslyn(
    repo_root: Path,
    *,
    repository_id: str,
    commit_sha: str,
    api_project_path: str = "",
) -> list[ApiOperationFact]:
    data = _run_extractor(
        repo_root,
        repository_id=repository_id,
        commit_sha=commit_sha,
        api_project_path=api_project_path,
    )
    facts: list[ApiOperationFact] = []
    for row in data.get("operations") or []:
        if not isinstance(row, dict):
            continue
        ev_list: list[Evidence] = []
        for ev in row.get("evidence") or []:
            if not isinstance(ev, dict):
                continue
            ev_list.append(
                Evidence(
                    repository_id=str(ev.get("repositoryId") or repository_id),
                    commit_sha=str(ev.get("commitSha") or commit_sha),
                    file_path=str(ev.get("filePath") or ""),
                    line_start=int(ev.get("lineStart") or 1),
                    line_end=int(ev.get("lineEnd") or 1),
                    detector_id=str(ev.get("detectorId") or DETECTOR_ID),
                    detector_version=str(ev.get("detectorVersion") or DETECTOR_VERSION),
                    confidence=float(ev.get("confidence") or 0.97),
                )
            )
        authz_source: AuthzSource = "unknown"
        src = str(row.get("authzSource") or "unknown")
        if src in ("attribute", "class-level", "convention", "unknown"):
            authz_source = src  # type: ignore[assignment]
        facts.append(
            ApiOperationFact(
                operation_key=str(row.get("operationKey") or ""),
                http_method=str(row.get("httpMethod") or "").upper(),
                http_path=str(row.get("httpPath") or "/"),
                controller=str(row.get("controller") or ""),
                action=str(row.get("action") or ""),
                authz_policy=(
                    str(row["authzPolicy"]) if row.get("authzPolicy") is not None else None
                ),
                authz_source=authz_source,
                read_only=bool(row.get("readOnly")),
                evidence=ev_list,
            )
        )
    return facts
