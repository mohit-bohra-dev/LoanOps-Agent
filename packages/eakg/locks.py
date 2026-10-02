"""Per-repository advisory file lock."""

from __future__ import annotations

import time
from pathlib import Path


class RepoLock:
    def __init__(self, lock_dir: str | Path, repository_id: str, *, timeout_s: float = 120.0) -> None:
        self.path = Path(lock_dir) / f"{repository_id}.lock"
        self.timeout_s = timeout_s
        self._held = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.time() + self.timeout_s
        while time.time() < deadline:
            try:
                fd = self.path.open("x", encoding="utf-8")
                fd.write(str(time.time()))
                fd.close()
                self._held = True
                return
            except FileExistsError:
                # stale lock > 1h
                try:
                    age = time.time() - self.path.stat().st_mtime
                    # Stale after 10 minutes (interrupted onboard leaves locks).
                    if age > 600:
                        self.path.unlink(missing_ok=True)
                        continue
                except OSError:
                    pass
                time.sleep(0.2)
        raise TimeoutError(f"could not acquire lock {self.path}")

    def release(self) -> None:
        if self._held:
            self.path.unlink(missing_ok=True)
            self._held = False

    def __enter__(self) -> RepoLock:
        self.acquire()
        return self

    def __exit__(self, *args: object) -> None:
        self.release()
