"""Contract tests for AbstractCredentialBroker (static + mock)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from packages.common.providers.credential_broker import (
    AccessToken,
    CachingCredentialBroker,
    CredentialNotConfigured,
    MockCredentialBroker,
    StaticCredentialBroker,
)
from packages.common.providers.testing import MockSecretsProvider


@pytest.fixture
def secrets() -> MockSecretsProvider:
    return MockSecretsProvider(
        secrets={
            "APP_TOKEN_FEES": "token-fees",
            "APP_TOKEN_ESCROW": "token-escrow",
        }
    )


@pytest.fixture
def static_broker(secrets: MockSecretsProvider) -> CachingCredentialBroker:
    inner = StaticCredentialBroker(
        secrets,
        shared_token="shared-bearer",
        shared_apps={"shared_app"},
    )
    return CachingCredentialBroker(inner)


@pytest.fixture
def mock_broker() -> CachingCredentialBroker:
    return CachingCredentialBroker(
        MockCredentialBroker(
            tokens={"fees": "mock-fees", "escrow": "mock-escrow"},
            denied={"denied_app"},
        )
    )


@pytest.mark.parametrize("broker_fixture", ["static_broker", "mock_broker"])
class TestCredentialBrokerContract:
    async def test_token_per_app(
        self, broker_fixture: str, request: pytest.FixtureRequest
    ) -> None:
        broker: CachingCredentialBroker = request.getfixturevalue(broker_fixture)
        app_id = "fees"
        if broker_fixture == "static_broker":
            await broker.prime(["fees", "escrow", "shared_app"])
        token = await broker.get_token(app_id, "https://aud.example")
        assert isinstance(token, AccessToken)
        assert token.application_id == app_id
        assert token.token.get_secret_value()
        assert token.token.get_secret_value() not in repr(token)

    async def test_unknown_app_raises(
        self, broker_fixture: str, request: pytest.FixtureRequest
    ) -> None:
        broker: CachingCredentialBroker = request.getfixturevalue(broker_fixture)
        if broker_fixture == "static_broker":
            await broker.prime(["fees"])
        with pytest.raises(CredentialNotConfigured):
            await broker.get_token("unknown_app", "aud")

    async def test_repr_hides_token(
        self, broker_fixture: str, request: pytest.FixtureRequest
    ) -> None:
        broker: CachingCredentialBroker = request.getfixturevalue(broker_fixture)
        app_id = "fees"
        if broker_fixture == "static_broker":
            await broker.prime(["fees"])
        token = await broker.get_token(app_id, "aud")
        text = repr(token)
        secret = token.token.get_secret_value()
        assert secret not in text

    async def test_check_no_secrets_io(
        self, broker_fixture: str, request: pytest.FixtureRequest
    ) -> None:
        if broker_fixture == "static_broker":

            class SpySecrets(MockSecretsProvider):
                def __init__(self) -> None:
                    super().__init__(secrets={"APP_TOKEN_FEES": "token-fees"})
                    self.calls = 0

                async def get(self, name: str) -> str:
                    self.calls += 1
                    return await super().get(name)

                async def get_or_default(self, name: str, default: str) -> str:
                    self.calls += 1
                    return await super().get_or_default(name, default)

            spy = SpySecrets()
            inner = StaticCredentialBroker(spy)
            broker = CachingCredentialBroker(inner)
            await broker.prime(["fees"])
            before = spy.calls
            check = await broker.check("fees", "aud")
            assert check.state == "configured"
            assert spy.calls == before
        else:
            broker: CachingCredentialBroker = request.getfixturevalue(broker_fixture)
            check = await broker.check("fees", "aud")
            assert check.state == "configured"
            missing = await broker.check("nope", "aud")
            assert missing.state == "missing"


class TestCachingCredentialBroker:
    async def test_single_flight(self) -> None:
        calls = {"n": 0}

        class Counting(MockCredentialBroker):
            async def get_token(  # type: ignore[override]
                self, application_id: str, audience: str, *, principal: Any = None
            ) -> AccessToken:
                calls["n"] += 1
                await asyncio.sleep(0.05)
                return await super().get_token(
                    application_id, audience, principal=principal
                )

        broker = CachingCredentialBroker(Counting(tokens={"fees": "t1"}))
        results = await asyncio.gather(
            *[broker.get_token("fees", "aud") for _ in range(10)]
        )
        assert calls["n"] == 1
        assert all(r.token.get_secret_value() == "t1" for r in results)

    async def test_invalidate(self) -> None:
        inner = MockCredentialBroker(tokens={"fees": "v1"})
        broker = CachingCredentialBroker(inner)
        t1 = await broker.get_token("fees", "aud")
        assert t1.token.get_secret_value() == "v1"
        inner._tokens["fees"] = "v2"
        t_cached = await broker.get_token("fees", "aud")
        assert t_cached.token.get_secret_value() == "v1"
        await broker.invalidate("fees", "aud")
        t2 = await broker.get_token("fees", "aud")
        assert t2.token.get_secret_value() == "v2"


class TestStaticSharedApps:
    async def test_shared_token_only_for_listed(
        self, secrets: MockSecretsProvider
    ) -> None:
        broker = StaticCredentialBroker(
            secrets, shared_token="shared", shared_apps={"shared_app"}
        )
        await broker.prime(["shared_app", "other"])
        tok = await broker.get_token("shared_app", "aud")
        assert tok.token.get_secret_value() == "shared"
        with pytest.raises(CredentialNotConfigured):
            await broker.get_token("other", "aud")
