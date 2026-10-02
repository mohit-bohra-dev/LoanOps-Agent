"""Clone / access helpers — always use glab against configured GitLab host."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote


def run_glab(
    args: list[str],
    *,
    host: str,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke glab with explicit hostname (never rely on gitlab.com default)."""
    cmd = ["glab", *args]
    # Insert --hostname after the subcommand group when possible.
    # Patterns: `api ...`, `repo clone ...`
    if args and args[0] == "api":
        cmd = ["glab", "api", "--hostname", host, *args[1:]]
    elif len(args) >= 2 and args[0] == "repo":
        cmd = ["glab", "repo", args[1], "--hostname", host, *args[2:]]
    else:
        cmd = ["glab", "--hostname", host, *args]
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def run_git(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Local git only (rev-parse, diff). Remote ops go through glab."""
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def path_with_namespace_from_url(git_url: str) -> str:
    """https://host/group/repo.git → group/repo"""
    m = re.match(r"https?://[^/]+/(.+?)(?:\.git)?/?$", git_url.strip())
    if m:
        return m.group(1).strip("/")
    m = re.match(r"ssh://git@[^/]+/(.+?)(?:\.git)?/?$", git_url.strip())
    if m:
        return m.group(1).strip("/")
    m = re.match(r"git@[^:]+:(.+?)(?:\.git)?/?$", git_url.strip())
    if m:
        return m.group(1).strip("/")
    return git_url.strip().removesuffix(".git")


def project_api_path(git_url: str) -> str:
    """URL-encode path for GitLab REST: group%2Frepo"""
    return quote(path_with_namespace_from_url(git_url), safe="")


def access_check(git_url: str, host: str) -> tuple[str, str]:
    """Return (access_status, detail). Uses glab api GET /projects/:id."""
    proj = project_api_path(git_url)
    proc = run_glab(["api", f"projects/{proj}"], host=host)
    if proc.returncode == 0 and proc.stdout.strip():
        try:
            data = json.loads(proc.stdout)
            name = data.get("path_with_namespace") or path_with_namespace_from_url(git_url)
            return "ok", f"glab api ok: {name}"
        except json.JSONDecodeError:
            return "ok", "glab api ok"
    err = (proc.stderr or proc.stdout or "").lower()
    if "401" in err or "403" in err or "unauthorized" in err or "forbidden" in err:
        return "auth_required", (proc.stderr or proc.stdout)[:500]
    if "404" in err:
        return "no_access", (proc.stderr or proc.stdout)[:500]
    return "no_access", (proc.stderr or proc.stdout)[:500]


def clone_or_fetch(
    git_url: str,
    dest: Path,
    *,
    host: str,
    branch: str = "main",
    recurse_submodules: bool = True,
) -> str:
    """Clone/update via glab repo clone; return HEAD commit sha."""
    path_ns = path_with_namespace_from_url(git_url)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if (dest / ".git").is_dir():
        # Refresh via glab-authenticated remote (git fetch still uses configured remotes
        # that glab set up with the host's credentials).
        run_git(["fetch", "--filter=blob:none", "origin", branch], cwd=dest)
        run_git(["checkout", branch], cwd=dest)
        run_git(["pull", "--ff-only", "origin", branch], cwd=dest)
        if recurse_submodules:
            run_git(
                ["submodule", "update", "--init", "--recursive", "--filter=blob:none"],
                cwd=dest,
            )
    else:
        if dest.exists() and any(dest.iterdir()):
            raise RuntimeError(f"clone dest not empty: {dest}")
        # glab repo clone <path> <dir> -- --gitflags
        gitflags = [
            "--",
            "--filter=blob:none",
            "--branch",
            branch,
            "--single-branch",
        ]
        if recurse_submodules:
            gitflags.append("--recurse-submodules")
        proc = run_glab(
            ["repo", "clone", path_ns, str(dest), *gitflags],
            host=host,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"glab repo clone failed: {(proc.stderr or proc.stdout)[:800]}"
            )

    head = run_git(["rev-parse", "HEAD"], cwd=dest)
    if head.returncode != 0:
        raise RuntimeError(head.stderr)
    return head.stdout.strip()


def remote_head(git_url: str, *, host: str, branch: str = "main") -> str | None:
    """Resolve branch tip SHA via glab api (not raw git ls-remote)."""
    proj = project_api_path(git_url)
    # GET /projects/:id/repository/branches/:branch
    branch_enc = quote(branch, safe="")
    proc = run_glab(
        ["api", f"projects/{proj}/repository/branches/{branch_enc}"],
        host=host,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        data = json.loads(proc.stdout)
        commit = data.get("commit") or {}
        return str(commit.get("id") or "") or None
    except json.JSONDecodeError:
        return None


def changed_files(repo: Path, from_commit: str, to_commit: str) -> list[str]:
    if not from_commit:
        return ["*"]
    proc = run_git(["diff", "--name-only", f"{from_commit}..{to_commit}"], cwd=repo)
    if proc.returncode != 0:
        return ["*"]
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
