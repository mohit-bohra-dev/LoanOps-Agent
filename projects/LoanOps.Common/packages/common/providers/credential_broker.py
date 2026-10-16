"""Credential broker — re-exports from provider_contracts.

LoanOps-specific destination resolution stays in ``auth0_destination.py``;
factory wires Auth0 destinations from the EAKG registry.
"""

from provider_contracts.credential_broker import (
    AbstractCredentialBroker,
    AccessToken,
    Auth0M2MCredentialBroker,
    CachingCredentialBroker,
    CredentialCheck,
    CredentialDenied,
    CredentialError,
    CredentialNotConfigured,
    CredentialUnavailable,
    MockCredentialBroker,
    Principal,
    StaticCredentialBroker,
    TokenSource,
    broker_token_source,
)

__all__ = [
    "AbstractCredentialBroker",
    "AccessToken",
    "Auth0M2MCredentialBroker",
    "CachingCredentialBroker",
    "CredentialCheck",
    "CredentialDenied",
    "CredentialError",
    "CredentialNotConfigured",
    "CredentialUnavailable",
    "MockCredentialBroker",
    "Principal",
    "StaticCredentialBroker",
    "TokenSource",
    "broker_token_source",
]
