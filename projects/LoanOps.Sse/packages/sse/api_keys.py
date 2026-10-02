"""Hashed API key store for MCP / agent callers."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


@dataclass
class ApiKeyRecord:
    key_id: str
    key_hash: str
    label: str
    scopes: list[str]
    created_at: str
    revoked: bool = False


@dataclass
class ApiKeyStore:
    """In-memory API key store (hash-only). Swap to Redis/DB later."""

    _keys: dict[str, ApiKeyRecord] = field(default_factory=dict)

    def register(self, label: str, scopes: list[str]) -> tuple[str, ApiKeyRecord]:
        raw = f"sse_{secrets.token_urlsafe(32)}"
        key_id = secrets.token_hex(8)
        record = ApiKeyRecord(
            key_id=key_id,
            key_hash=hash_api_key(raw),
            label=label,
            scopes=list(scopes),
            created_at=datetime.now(UTC).isoformat(),
        )
        self._keys[key_id] = record
        return raw, record

    def verify(self, raw_key: str) -> ApiKeyRecord | None:
        digest = hash_api_key(raw_key)
        for record in self._keys.values():
            if not record.revoked and secrets.compare_digest(record.key_hash, digest):
                return record
        return None

    def revoke(self, key_id: str) -> bool:
        record = self._keys.get(key_id)
        if record is None:
            return False
        record.revoked = True
        return True
