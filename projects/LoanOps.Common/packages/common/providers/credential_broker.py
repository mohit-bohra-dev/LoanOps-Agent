"""Credential broker — per-app access tokens for live SSE invoke and spec fetch.

Protocol + static/mock/caching implementations live here (precedent: loan_data.py).
Only ``factory.get_credential_broker`` imports the concrete classes.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, SecretStr
from provider_contracts.secrets import AbstractSecretsProvider

TokenSource = Callable[[str, str], Awaitable[str]]


class CredentialError(Exception):
    """Base error for credential broker failures."""

    def __init__(self, application_id: str, message: str) -> None:
        self.application_id = application_id
        super().__init__(message)


class CredentialNotConfigured(CredentialError):
    """No access arrangement for this application."""


class CredentialDenied(CredentialError):
    """Issuer refused (revoked / not entitled)."""


class CredentialUnavailable(CredentialError):
    """Issuer unreachable."""


class AccessToken(BaseModel):
    """In-memory token; never persist or log ``token``."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    application_id: str
    audience: str
    token: SecretStr
    token_type: Literal["Bearer"] = "Bearer"
    expires_at: datetime | None = None


class Principal(BaseModel):
    """Reserved for on-behalf-of (FR-011). Unused by static/mock brokers."""

    user_id: str | None = None
    tenant: str | None = None
    subject_token: SecretStr | None = None


class CredentialCheck(BaseModel):
    application_id: str
    state: Literal["configured", "missing", "error"]
    detail: str | None = None


class AbstractCredentialBroker(ABC):
    """Per-app credential surface for invoke and spec refresh."""

    @abstractmethod
    async def get_token(
        self,
        application_id: str,
        audience: str,
        *,
        principal: Principal | None = None,
    ) -> AccessToken: ...

    @abstractmethod
    async def invalidate(self, application_id: str, audience: str) -> None: ...

    @abstractmethod
    async def check(self, application_id: str, audience: str) -> CredentialCheck:
        """Answer from in-memory state only — MUST NOT do network I/O."""

    async def prime(self, application_ids: Sequence[str]) -> None:
        """Optional warm-up (e.g. secret presence). Default no-op."""
        return None


class StaticCredentialBroker(AbstractCredentialBroker):
    """Local/dev broker: ``APP_TOKEN_<APPID>`` secrets + optional shared token opt-in."""

    def __init__(
        self,
        secrets: AbstractSecretsProvider,
        shared_token: str = "",
        shared_apps: set[str] | frozenset[str] | None = None,
    ) -> None:
        self._secrets = secrets
        self._shared_token = shared_token
        self._shared_apps: frozenset[str] = frozenset(shared_apps or ())
        self._present: set[str] = set()
        self._errored: set[str] = set()
        self._primed: set[str] = set()

    async def prime(self, application_ids: Sequence[str]) -> None:
        for app_id in application_ids:
            self._primed.add(app_id)
            name = f"APP_TOKEN_{app_id.upper()}"
            try:
                value = await self._secrets.get_or_default(name, "")
            except Exception:  # noqa: BLE001 — presence probe must never raise
                self._errored.add(app_id)
                self._present.discard(app_id)
                continue
            if value:
                self._present.add(app_id)
                self._errored.discard(app_id)
            else:
                self._present.discard(app_id)

    async def get_token(
        self,
        application_id: str,
        audience: str,
        *,
        principal: Principal | None = None,
    ) -> AccessToken:
        _ = principal
        name = f"APP_TOKEN_{application_id.upper()}"
        value = await self._secrets.get_or_default(name, "")
        if value:
            return AccessToken(
                application_id=application_id,
                audience=audience,
                token=SecretStr(value),
            )
        if application_id in self._shared_apps and self._shared_token:
            return AccessToken(
                application_id=application_id,
                audience=audience,
                token=SecretStr(self._shared_token),
            )
        raise CredentialNotConfigured(
            application_id,
            f"No credential configured for application '{application_id}'",
        )

    async def invalidate(self, application_id: str, audience: str) -> None:
        _ = audience
        # Static tokens have no cache; presence sets unchanged until next prime.
        self._present.discard(application_id)

    async def check(self, application_id: str, audience: str) -> CredentialCheck:
        _ = audience
        if application_id in self._errored:
            return CredentialCheck(
                application_id=application_id, state="error", detail="secret_lookup_failed"
            )
        if application_id in self._present:
            return CredentialCheck(application_id=application_id, state="configured")
        if application_id in self._shared_apps and self._shared_token:
            return CredentialCheck(application_id=application_id, state="configured")
        if application_id not in self._primed:
            return CredentialCheck(
                application_id=application_id, state="error", detail="unknown"
            )
        return CredentialCheck(application_id=application_id, state="missing")


class MockCredentialBroker(AbstractCredentialBroker):
    """In-memory broker for tests and contract tests."""

    def __init__(
        self,
        tokens: dict[str, str],
        denied: set[str] | frozenset[str] | None = None,
        unavailable: set[str] | frozenset[str] | None = None,
    ) -> None:
        self._tokens = dict(tokens)
        self._denied: frozenset[str] = frozenset(denied or ())
        self._unavailable: frozenset[str] = frozenset(unavailable or ())

    async def get_token(
        self,
        application_id: str,
        audience: str,
        *,
        principal: Principal | None = None,
    ) -> AccessToken:
        _ = principal
        if application_id in self._unavailable:
            raise CredentialUnavailable(
                application_id, f"Credential issuer unavailable for '{application_id}'"
            )
        if application_id in self._denied:
            raise CredentialDenied(
                application_id, f"Access denied for '{application_id}'"
            )
        value = self._tokens.get(application_id)
        if not value:
            raise CredentialNotConfigured(
                application_id,
                f"No credential configured for application '{application_id}'",
            )
        return AccessToken(
            application_id=application_id,
            audience=audience,
            token=SecretStr(value),
        )

    async def invalidate(self, application_id: str, audience: str) -> None:
        _ = (application_id, audience)

    async def check(self, application_id: str, audience: str) -> CredentialCheck:
        _ = audience
        if application_id in self._unavailable or application_id in self._denied:
            return CredentialCheck(
                application_id=application_id,
                state="error",
                detail="CredentialDenied" if application_id in self._denied else "CredentialUnavailable",
            )
        if application_id in self._tokens and self._tokens[application_id]:
            return CredentialCheck(application_id=application_id, state="configured")
        return CredentialCheck(application_id=application_id, state="missing")


class CachingCredentialBroker(AbstractCredentialBroker):
    """Single-flight token cache wrapping an inner broker (spec §3.7)."""

    def __init__(self, inner: AbstractCredentialBroker, *, skew_seconds: float = 60.0) -> None:
        self._inner = inner
        self._skew = timedelta(seconds=skew_seconds)
        self._cache: dict[tuple[str, str, str], AccessToken] = {}
        self._locks: dict[tuple[str, str, str], asyncio.Lock] = {}
        self._locks_guard = asyncio.Lock()
        self._last_state: dict[tuple[str, str], CredentialCheck] = {}

    def _key(
        self, application_id: str, audience: str, principal: Principal | None
    ) -> tuple[str, str, str]:
        principal_key = principal.user_id if principal and principal.user_id else "-"
        return (application_id, audience, principal_key)

    def _fresh(self, token: AccessToken, now: datetime) -> bool:
        if token.expires_at is None:
            return True
        return token.expires_at - self._skew > now

    async def _lock_for(self, key: tuple[str, str, str]) -> asyncio.Lock:
        async with self._locks_guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock
            return lock

    async def get_token(
        self,
        application_id: str,
        audience: str,
        *,
        principal: Principal | None = None,
    ) -> AccessToken:
        key = self._key(application_id, audience, principal)
        now = datetime.now(UTC)
        cached = self._cache.get(key)
        if cached is not None and self._fresh(cached, now):
            return cached
        lock = await self._lock_for(key)
        async with lock:
            cached = self._cache.get(key)
            if cached is not None and self._fresh(cached, datetime.now(UTC)):
                return cached
            try:
                token = await self._inner.get_token(
                    application_id, audience, principal=principal
                )
            except CredentialNotConfigured as exc:
                self._last_state[(application_id, audience)] = CredentialCheck(
                    application_id=application_id, state="missing"
                )
                raise exc
            except CredentialDenied as exc:
                self._last_state[(application_id, audience)] = CredentialCheck(
                    application_id=application_id,
                    state="error",
                    detail="CredentialDenied",
                )
                raise exc
            except CredentialUnavailable as exc:
                self._last_state[(application_id, audience)] = CredentialCheck(
                    application_id=application_id,
                    state="error",
                    detail="CredentialUnavailable",
                )
                raise exc
            self._cache[key] = token
            self._last_state[(application_id, audience)] = CredentialCheck(
                application_id=application_id, state="configured"
            )
            return token

    async def invalidate(self, application_id: str, audience: str) -> None:
        drop = [k for k in self._cache if k[0] == application_id and k[1] == audience]
        for key in drop:
            del self._cache[key]
        await self._inner.invalidate(application_id, audience)

    async def check(self, application_id: str, audience: str) -> CredentialCheck:
        known = self._last_state.get((application_id, audience))
        if known is not None:
            return known
        for key, token in self._cache.items():
            if key[0] == application_id and key[1] == audience and self._fresh(
                token, datetime.now(UTC)
            ):
                return CredentialCheck(application_id=application_id, state="configured")
        return await self._inner.check(application_id, audience)

    async def prime(self, application_ids: Sequence[str]) -> None:
        await self._inner.prime(application_ids)


def broker_token_source(broker: AbstractCredentialBroker) -> TokenSource:
    """Build a ``TokenSource`` that uses the broker; missing creds → empty string."""

    async def source(application_id: str, audience: str) -> str:
        try:
            access = await broker.get_token(application_id, audience)
        except CredentialNotConfigured:
            return ""
        except CredentialError:
            return ""
        return access.token.get_secret_value()

    return source
