"""Orchestrate spec refresh → build → reindex (Phase 3)."""

from __future__ import annotations

from typing import Any


async def refresh_app(*, repository_id: str, environment: str) -> dict[str, Any]:
    return {"repository_id": repository_id, "environment": environment, "status": "not_implemented"}


async def refresh_all(*, environment: str) -> dict[str, Any]:
    return {"environment": environment, "status": "not_implemented"}
