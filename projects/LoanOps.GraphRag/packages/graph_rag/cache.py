"""Extraction cache keyed by content + model + prompt + schema versions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def cache_key(
    content: str,
    *,
    model_id: str,
    prompt_version: str,
    schema_version: str,
) -> str:
    blob = "|".join([content, model_id, prompt_version, schema_version]).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def cache_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / f"{key}.json"


def read_cache(cache_dir: Path, key: str) -> dict[str, Any] | None:
    path = cache_path(cache_dir, key)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_cache(cache_dir: Path, key: str, payload: dict[str, Any]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_path(cache_dir, key)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
