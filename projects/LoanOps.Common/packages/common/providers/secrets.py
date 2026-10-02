"""Secrets provider protocol — re-exports from provider_contracts."""

from provider_contracts.secrets import AbstractSecretsProvider as SecretsProvider

__all__ = ["SecretsProvider"]
