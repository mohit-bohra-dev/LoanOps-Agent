"""Optional in-process nightly refresh scheduler (spec §9.6)."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from packages.eakg.locks import RepoLock

logger = logging.getLogger(__name__)


def seconds_until_hour_utc(hour: int, *, now: datetime | None = None) -> float:
    """Seconds until the next ``hour`` UTC (0–23)."""
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    else:
        current = current.astimezone(UTC)
    target = current.replace(hour=hour % 24, minute=0, second=0, microsecond=0)
    if target <= current:
        target = target + timedelta(days=1)
    return max(0.0, (target - current).total_seconds())


async def run_nightly_locked(
    *,
    environment: str,
    workspace_dir: str | Path,
    lock_name: str = "api_index_refresh",
    timeout_s: float = 30.0,
) -> dict[str, Any] | None:
    """Acquire file lock then run ``refresh_nightly``. Returns None if lock busy."""
    from packages.api_index.refresh import refresh_nightly

    lock = RepoLock(Path(workspace_dir) / ".locks", lock_name, timeout_s=timeout_s)
    try:
        lock.acquire()
    except TimeoutError:
        logger.info("api_index nightly skipped — lock held (%s)", lock_name)
        return None
    try:
        return await refresh_nightly(environment=environment)
    finally:
        lock.release()


async def scheduler_loop(
    *,
    environment: str,
    nightly_hour: int,
    workspace_dir: str | Path,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Sleep until nightly_hour UTC, refresh under lock, repeat until stopped."""
    stop = stop_event or asyncio.Event()
    while not stop.is_set():
        delay = seconds_until_hour_utc(nightly_hour)
        try:
            await asyncio.wait_for(stop.wait(), timeout=delay)
            break
        except TimeoutError:
            pass
        try:
            report = await run_nightly_locked(
                environment=environment,
                workspace_dir=workspace_dir,
            )
            if report is not None:
                logger.info(
                    "api_index nightly done status=%s changed=%s",
                    report.get("status"),
                    report.get("changed"),
                )
        except Exception:  # noqa: BLE001
            logger.exception("api_index nightly refresh failed")


def start_scheduler_task(
    *,
    environment: str,
    nightly_hour: int,
    workspace_dir: str | Path,
    enabled: bool,
) -> asyncio.Task[None] | None:
    """Start background nightly task when ``enabled``; else None."""
    if not enabled:
        return None
    return asyncio.create_task(
        scheduler_loop(
            environment=environment,
            nightly_hour=nightly_hour,
            workspace_dir=workspace_dir,
        ),
        name="api_index_nightly_scheduler",
    )


_scheduler_task: asyncio.Task[None] | None = None


def ensure_scheduler_started(
    *,
    environment: str,
    nightly_hour: int,
    workspace_dir: str | Path,
    enabled: bool,
) -> asyncio.Task[None] | None:
    """Idempotent start for Agent API / MCP lifespan."""
    global _scheduler_task
    if not enabled:
        return None
    if _scheduler_task is not None and not _scheduler_task.done():
        return _scheduler_task
    _scheduler_task = start_scheduler_task(
        environment=environment,
        nightly_hour=nightly_hour,
        workspace_dir=workspace_dir,
        enabled=True,
    )
    return _scheduler_task


async def stop_scheduler() -> None:
    """Cancel in-process scheduler (tests / shutdown)."""
    global _scheduler_task
    if _scheduler_task is None:
        return
    _scheduler_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await _scheduler_task
    _scheduler_task = None
