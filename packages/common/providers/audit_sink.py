"""Audit sink provider protocol — re-exports from provider_contracts."""

from provider_contracts.audit_sink import AbstractAuditSinkProvider as AuditSinkProvider
from provider_contracts.audit_sink import AuditEvent

__all__ = ["AuditSinkProvider", "AuditEvent"]
